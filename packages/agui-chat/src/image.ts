/**
 * Phone photos are often 5-15 MB. Before upload, a big photo is redrawn at most `maxSide` px and saved
 * as JPEG: uploads get many times faster and the file fits what the model accepts. PDFs, text and
 * small images are sent unchanged; anything that cannot be decoded is sent as it is.
 */
export async function shrinkImage(file: File, maxSide = 2000, maxBytes = 1_500_000): Promise<File> {
  if (!maxSide || !/^image\/(jpeg|png|webp|heic|heif)$/.test(file.type) || typeof createImageBitmap !== 'function') return file
  let bmp: ImageBitmap
  try { bmp = await createImageBitmap(file) } catch { return file }
  const scale = Math.min(1, maxSide / Math.max(bmp.width, bmp.height))
  if (scale === 1 && file.size <= maxBytes) { bmp.close?.(); return file }
  const canvas = document.createElement('canvas')
  canvas.width = Math.round(bmp.width * scale)
  canvas.height = Math.round(bmp.height * scale)
  const g = canvas.getContext('2d')
  if (!g) return file
  g.fillStyle = '#fff'                // transparent PNG areas become white in the JPEG
  g.fillRect(0, 0, canvas.width, canvas.height)
  g.drawImage(bmp, 0, 0, canvas.width, canvas.height)
  bmp.close?.()
  const blob = await new Promise<Blob | null>((ok) => canvas.toBlob(ok, 'image/jpeg', 0.85))
  if (!blob || blob.size >= file.size) return file
  return new File([blob], file.name.replace(/\.[^.]+$/, '') + '.jpg', { type: 'image/jpeg', lastModified: file.lastModified })
}
