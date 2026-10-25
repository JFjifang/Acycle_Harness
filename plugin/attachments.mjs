/** Session-authorized data import and durable MATLAB output delivery. No science occurs here. */
import { createHash, randomUUID } from 'node:crypto'
import { constants } from 'node:fs'
import { open, readFile, lstat, realpath, mkdir, link, unlink } from 'node:fs/promises'
import { basename, extname, isAbsolute, join, relative, resolve, sep } from 'node:path'

const INPUT_EXTENSIONS = new Set(['.csv', '.txt', '.dat', '.tsv'])
const OUTPUT_EXTENSIONS = new Set(['.csv', '.mat', '.png', '.fig', '.pdf', '.json'])
const RUN_ID = /^[0-9]{8}T[0-9]{6}Z-[a-f0-9]{12}$/
const digest = data => createHash('sha256').update(data).digest('hex')
const contained = (root, file) => { const rel = relative(root, file); return rel === '' || (!rel.startsWith('..' + sep) && rel !== '..' && !isAbsolute(rel)) }
const getService = (ctx, name) => ctx.get(name)

export function deliveryConfig(config = {}) {
  const result = {
    maxImportBytes: config.maxImportBytes ?? 32 * 1024 * 1024,
    maxArtifactBytes: config.maxArtifactBytes ?? 64 * 1024 * 1024,
    maxPreviewImages: config.maxPreviewImages ?? 4,
    maxFileAttachments: config.maxFileAttachments ?? 24,
    maxDeliveryRuns: config.maxDeliveryRuns ?? 3,
    presentOutputs: config.presentOutputs ?? true,
  }
  for (const [key, value] of Object.entries(result)) {
    if (key === 'presentOutputs') { if (typeof value !== 'boolean') throw new Error(`${key} must be boolean`) }
    else if (!Number.isSafeInteger(value) || value < 1) throw new Error(`${key} must be a positive integer`)
  }
  return result
}

/** Only user-uploaded references in this exact Session may be imported. */
export async function sessionFiles(ctx, exec) {
  if (!exec.agent) throw new Error('Attachment import requires an active Harness Session; use a workspace file path outside Harness.')
  const attachments = getService(ctx, 'attachments')
  const query = getService(ctx, 'sessionQuery')
  if (!attachments || !query) throw new Error('Attachment import requires the Harness attachments and sessionQuery services.')
  const observation = await query.observeSession(exec.agent.id, { projectionMode: 'none', signal: exec.signal })
  try {
    const groups = []
    for (const event of observation.events) {
      if (event.type !== 'user/message' || event.data.source?.kind !== 'user') continue
      const refs = event.data.content.filter(part => part.type === 'file').map(part => part.attachment)
      if (refs.length) groups.push({ message_id: event.data.id, refs })
    }
    return { attachments, groups }
  } finally { observation[Symbol.dispose]() }
}

function safeFilename(name) {
  const leaf = basename(name.replaceAll('\\', '/')).replace(/[\u0000-\u001f\u007f]/g, '_')
  if (!INPUT_EXTENSIONS.has(extname(leaf).toLowerCase())) throw new Error('Acycle data attachments must be two-column CSV, TXT, DAT or TSV files. Convert other formats explicitly before analysis.')
  if (!leaf || leaf === '.' || leaf === '..') throw new Error('Invalid attachment filename')
  return leaf
}

async function secureDirectory(root, components) {
  let current = root
  for (const component of components) {
    current = join(current, component)
    try { await mkdir(current) } catch (error) { if (error.code !== 'EEXIST') throw error }
    const info = await lstat(current)
    if (info.isSymbolicLink() || !info.isDirectory()) throw new Error('Acycle attachment storage must use real directories inside the workspace')
    if (!contained(root, await realpath(current))) throw new Error('Attachment destination escaped the workspace')
  }
  return current
}

async function importRef(attachments, ref, messageId, workspace, exec, config) {
  const name = safeFilename(ref.name)
  if (!Number.isSafeInteger(ref.bytes) || ref.bytes < 0 || ref.bytes > config.maxImportBytes) throw new Error('Attachment exceeds the configured import byte limit')
  await mkdir(workspace, { recursive: true })
  const root = await realpath(workspace)
  const directory = await secureDirectory(root, ['.acycle', 'imports'])
  const temporary = join(directory, `.import-${randomUUID()}`)
  const stream = await open(temporary, 'wx', 0o600)
  let bytes = 0
  const hash = createHash('sha256')
  try {
    for await (const chunk of attachments.readFileStream(ref, exec.signal)) {
      exec.signal.throwIfAborted()
      bytes += chunk.byteLength
      if (bytes > config.maxImportBytes || bytes > ref.bytes) throw new Error('Attachment byte length exceeds its admitted reference or import limit')
      hash.update(chunk)
      await stream.writeFile(chunk)
    }
    await stream.close()
    if (bytes !== ref.bytes) throw new Error('Attachment byte length does not match its admitted reference')
    const sha256 = hash.digest('hex')
    const admittedHash = ref.attachmentId.replace(/^sha256:/, '')
    if (/^[a-f0-9]{64}$/.test(admittedHash) && admittedHash !== sha256) throw new Error('Attachment digest does not match its admitted reference')
    const targetDirectory = await secureDirectory(root, ['.acycle', 'imports', sha256])
    const destination = join(targetDirectory, name)
    try { await link(temporary, destination) }
    catch (error) {
      if (error.code !== 'EEXIST') throw error
      const info = await lstat(destination)
      if (!info.isFile() || info.isSymbolicLink() || digest(await readFile(destination)) !== sha256) throw new Error('Existing imported file differs; refusing to overwrite it')
    }
    const result = { status: 'imported', input_path: destination, original_name: ref.name,
      bytes, sha256, attachment: ref, source_message_id: messageId, source_session_id: exec.agent.id,
      transformation: 'Verbatim byte copy only; scientific preparation remains in MATLAB.' }
    const receipt = destination + '.source.json'
    try {
      const file = await open(receipt, 'wx', 0o600)
      try { await file.writeFile(JSON.stringify(result, null, 2) + '\n') } finally { await file.close() }
    } catch (error) {
      if (error.code !== 'EEXIST') throw error
      const info = await lstat(receipt)
      if (info.isSymbolicLink() || !info.isFile()) throw new Error('Imported source receipt must be a regular file')
      const prior = JSON.parse(await readFile(receipt, 'utf8'))
      if (prior.sha256 !== sha256 || prior.input_path !== destination) throw new Error('Imported source receipt does not match the preserved input')
    }
    return { ...result, import_receipt: receipt }
  } finally {
    await stream.close()
    try { await unlink(temporary) } catch (error) { if (error.code !== 'ENOENT') throw error }
  }
}

export async function importAttachment(ctx, args, workspace, exec, config) {
  const { attachments, groups } = await sessionFiles(ctx, exec)
  const candidates = args.attachment_id
    ? groups.flatMap(group => group.refs.map(ref => ({ ref, messageId: group.message_id })))
      .filter(item => item.ref.attachmentId === args.attachment_id)
    : (groups.at(-1)?.refs ?? []).map(ref => ({ ref, messageId: groups.at(-1).message_id }))
  if (candidates.length === 0) throw new Error('No matching user file attachment exists in this Session. Upload a CSV/TXT/DAT/TSV or provide a workspace path.')
  const unique = [...new Map(candidates.map(item => [`${item.ref.attachmentId}:${item.ref.name}`, item])).values()]
  if (!args.attachment_id && unique.length > 1) return { status: 'selection_required',
    attachments: unique.map(({ ref }) => ref), note: 'Choose attachment_id from this list using the user question; do not guess the scientific dataset.' }
  const selected = unique.at(-1)
  return importRef(attachments, selected.ref, selected.messageId, workspace, exec, config)
}

/** Accept an uploaded file's exact official host path or unambiguous display name, not arbitrary external paths. */
export async function resolveInputAttachment(ctx, args, workspace, exec, config) {
  if (typeof args.input_path !== 'string' || !exec.agent || !getService(ctx, 'attachments') || !getService(ctx, 'sessionQuery')) return { args }
  const candidate = resolve(workspace, args.input_path)
  const roots = [workspace, process.env.ACYCLE_ROOT].filter(Boolean)
  try {
    const actual = await realpath(candidate)
    if (roots.some(root => contained(resolve(root), actual))) return { args }
  } catch (error) { if (error.code !== 'ENOENT') throw error }
  const { attachments, groups } = await sessionFiles(ctx, exec)
  const matches = groups.flatMap(group => group.refs.map(ref => ({ ref, messageId: group.message_id })))
    .filter(({ ref }) => {
      const hostPath = attachments.fileHostPath(ref)
      return hostPath === candidate || (args.input_path === ref.name && basename(args.input_path) === args.input_path)
    })
  const distinct = [...new Map(matches.map(item => [`${item.ref.attachmentId}:${item.ref.name}`, item])).values()]
  if (distinct.length === 0) return { args }
  if (distinct.length > 1) throw new Error('Multiple Session attachments match that filename; call acycle_import_attachment with an explicit attachment_id.')
  const imported = await importRef(attachments, distinct[0].ref, distinct[0].messageId, workspace, exec, config)
  return { args: { ...args, input_path: imported.input_path }, imported }
}

function compactProvenance(value) {
  if (!value || typeof value !== 'object') return value
  const { files, ...rest } = value
  return { ...rest, ...(Array.isArray(files) ? { source_file_count: files.length,
    source_mismatches: files.filter(file => file.matches_reference === false) } : {}) }
}

/** Keep numerical summaries and all caveats; omit repeated full source registries. */
export function modelValue(value) {
  if (!value || typeof value !== 'object' || Array.isArray(value)) return value
  const { result, presentation, ...rest } = value
  if (rest.provenance) rest.provenance = compactProvenance(rest.provenance)
  if (Array.isArray(rest.runs)) rest.runs = rest.runs.map(modelValue)
  if (result) {
    const { provenance, artifacts, summary, parameters, ...details } = result
    rest.matlab_result = { ...details, ...(!rest.summary && summary ? { summary } : {}),
      ...(!rest.parameters && parameters ? { parameters } : {}),
      ...(!rest.artifacts && artifacts ? { artifacts } : {}),
      ...(!rest.provenance && provenance ? { provenance: compactProvenance(provenance) } : {}) }
  }
  if (presentation) rest.presentation = { status: presentation.status, model_visual_inspection: false,
    preview_count: presentation.images.length, downloadable_file_count: presentation.files.length,
    display_markdown: presentation.display_markdown, delivery: presentation.delivery,
    warnings: presentation.warnings, skipped: presentation.skipped }
  return rest
}

export function renderResult(_args, value) {
  const blocks = [{ type: 'text', text: JSON.stringify(modelValue(value)) }]
  for (const item of value.presentation?.images ?? []) blocks.push({ type: 'image', attachment: item.attachment, offloaded: true })
  for (const item of value.presentation?.files ?? []) blocks.push({ type: 'file', attachment: item.attachment })
  return blocks
}

async function artifactBytes(workspace, runId, path, maxBytes) {
  const root = await realpath(workspace)
  const expected = join(root, '.acycle', 'runs', runId, 'outputs')
  const actual = await realpath(path)
  if (!contained(expected, actual)) throw new Error('Artifact is outside its recorded run output directory')
  const handle = await open(actual, constants.O_RDONLY | (constants.O_NOFOLLOW ?? 0))
  try {
    const info = await handle.stat()
    if (!info.isFile() || info.size > maxBytes) throw new Error('Artifact is not a regular file within the configured delivery byte limit')
    const data = await handle.readFile()
    if (data.length > maxBytes) throw new Error('Artifact exceeds the configured delivery byte limit')
    return data
  } finally { await handle.close() }
}

function displayPriority([key, path]) {
  if (extname(path).toLowerCase() !== '.png') return 10
  if (/evolution|evofft/i.test(key)) return 0
  if (/spectrum|figure_1/i.test(key)) return 1
  if (/figure_2/i.test(key)) return 2
  return 3
}

export async function attachOutputs(ctx, value, workspace, exec, config, fetchRun) {
  const sourceRuns = value.run_id && value.artifacts ? [value] : (Array.isArray(value.runs) ? value.runs : [])
  if (!sourceRuns.length) return value
  const attachments = getService(ctx, 'attachments')
  const presentation = { status: 'available', images: [], files: [], display_markdown: '',
    model_visual_inspection: false, warnings: [], skipped: [], delivery: { status: 'not_requested' } }
  if (!attachments) {
    presentation.status = 'paths_only'
    presentation.warnings.push('Harness attachment storage is unavailable; MATLAB output paths remain available.')
    return { ...value, presentation }
  }
  const allPaths = new Set()
  const records = []
  for (const item of sourceRuns.slice(0, config.maxDeliveryRuns)) {
    if (!RUN_ID.test(item.run_id ?? '')) continue
    records.push(item.artifacts ? item : await fetchRun(item.run_id))
  }
  if (sourceRuns.length > records.length) presentation.skipped.push({ reason: 'delivery_run_limit', count: sourceRuns.length - records.length })
  for (const record of records) {
    for (const [key, path] of Object.entries(record.artifacts ?? {}).sort((a, b) => displayPriority(a) - displayPriority(b))) {
      exec.signal.throwIfAborted()
      if (allPaths.has(path) || !OUTPUT_EXTENSIONS.has(extname(path).toLowerCase())) continue
      allPaths.add(path)
      if (presentation.files.length >= config.maxFileAttachments) { presentation.skipped.push({ path, reason: 'file_attachment_limit' }); continue }
      try {
        const data = await artifactBytes(workspace, record.run_id, path, config.maxArtifactBytes)
        const file = await attachments.saveFile({ data, name: `${record.run_id}-${basename(path)}` })
        const entry = { run_id: record.run_id, key, path, sha256: digest(data), attachment: file }
        presentation.files.push(entry)
        if (extname(path).toLowerCase() === '.png' && presentation.images.length < config.maxPreviewImages) {
          const image = await attachments.saveImage({ data, name: basename(path), mediaType: 'image/png' })
          presentation.images.push({ run_id: record.run_id, key, path, original_sha256: entry.sha256, attachment: image,
            note: 'Harness may resize this display preview; the original MATLAB PNG is also attached verbatim.' })
        }
      } catch (error) {
        exec.signal.throwIfAborted()
        presentation.skipped.push({ path, reason: error.message })
      }
    }
  }
  const imageLines = presentation.images.map(item => `![${item.run_id}: ${item.key}](<${item.path}>)`)
  const fileLines = presentation.files.filter(item => !item.path.endsWith('.png')).map(item => `[${item.run_id}: ${item.key}](<${item.path}>)`)
  presentation.display_markdown = [...imageLines, ...fileLines].join('\n\n')
  presentation.warnings.push('Image previews are delivered for the user; the model received offloaded references, not image pixels. Do not claim visual inspection. Include relevant display_markdown images and file links in the answer.')
  if (presentation.skipped.length) presentation.status = 'partial'
  if (config.presentOutputs && exec.agent && ctx.tools.get('present', exec.agent)) {
    const pngPaths = presentation.images.map(item => item.path)
    const usefulFiles = presentation.files.filter(item => ['.csv', '.mat'].includes(extname(item.path).toLowerCase()))
      .sort((a, b) => Number(b.path.endsWith('.mat')) - Number(a.path.endsWith('.mat'))).map(item => item.path)
    const paths = [...new Set([...pngPaths.slice(0, 3), ...usefulFiles])].slice(0, 4)
    if (paths.length) {
      try {
        const result = await ctx.tools.execute({ callId: `acycle-present-${randomUUID()}`, name: 'present',
          arguments: { files: paths.map(path => ({ path, description: 'Acycle original MATLAB output' })) },
          agent: exec.agent, parent: exec.token, rootCallId: exec.rootCallId, signal: exec.signal })
        presentation.delivery = result.isError ? { status: 'failed', error: result.error ?? result.content } : { status: 'presented', paths }
        if (result.isError) { presentation.status = 'partial'; presentation.warnings.push('The official Harness deliverable presentation failed; use the returned file links.') }
      } catch (error) {
        exec.signal.throwIfAborted()
        presentation.status = 'partial'
        presentation.delivery = { status: 'failed', error: error.message }
        presentation.warnings.push('MATLAB computation is complete; only Harness presentation failed. Reopen this run instead of recomputing it.')
      }
    }
  } else {
    presentation.delivery = { status: 'links_only', reason: 'The official present tool or active Session is unavailable.' }
  }
  return { ...value, presentation }
}
