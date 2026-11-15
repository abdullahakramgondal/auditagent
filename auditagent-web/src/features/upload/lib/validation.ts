/** The backend refuses a file above this size (api/app.py MAX_BYTES). */
export const MAX_BYTES = 10 * 1024 * 1024
const PDF_HEADER = '%PDF'

/** The first bytes of a file as text (the browser type of a file is not reliable for PDFs). */
function readHead(file: Blob): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => {
      const bytes = new Uint8Array(reader.result as ArrayBuffer)
      resolve(String.fromCharCode(...bytes))
    }
    reader.onerror = () => reject(reader.error)
    reader.readAsArrayBuffer(file.slice(0, PDF_HEADER.length))
  })
}

/** Why this file cannot start an audit, or null if it can. The same checks as the backend. */
export async function validatePdf(file: File): Promise<string | null> {
  if (file.size === 0) return 'This file is empty.'
  if (file.size > MAX_BYTES) return `This file is larger than ${MAX_BYTES / 1024 / 1024} MB.`
  let head: string
  try {
    head = await readHead(file)
  } catch {
    return 'This file cannot be read.'
  }
  if (head !== PDF_HEADER) return 'This is not a PDF file.'
  return null
}

/** 500 -> "500 B", 2048 -> "2 KB", 1572864 -> "1.5 MB". */
export function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)} KB`
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`
}

/** The same file chosen twice (for example the contract also put in the invoice slot). */
export function sameFile(a: File, b: File): boolean {
  return a.name === b.name && a.size === b.size && a.lastModified === b.lastModified
}