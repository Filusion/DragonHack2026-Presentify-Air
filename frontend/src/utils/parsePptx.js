/**
 * parsePptx.js
 * Extracts slides from a .pptx file in the browser using JSZip.
 * Returns an array of { title, content, notes, index } objects.
 *
 * Place this file at: src/utils/parsePptx.js
 * Add JSZip to your project:  npm install jszip
 */

import JSZip from 'jszip'

/**
 * Extract all text from an XML element's <a:t> nodes.
 */
function extractText(xml) {
  const matches = xml.match(/<a:t[^>]*>([^<]*)<\/a:t>/g) || []
  return matches
    .map(m => m.replace(/<[^>]+>/g, '').trim())
    .filter(Boolean)
    .join(' ')
}

/**
 * Try to pick a "title" from the slide XML by looking for
 * placeholder type="title" or type="ctrTitle" first,
 * then fall back to the first non-empty text run.
 */
function extractTitle(xml) {
  // find all <p:sp> blocks
  const spBlocks = xml.match(/<p:sp[\s\S]*?<\/p:sp>/g) || []

  for (const sp of spBlocks) {
    if (/type="title"|type="ctrTitle"/i.test(sp)) {
      const text = extractText(sp)
      if (text) return text
    }
  }

  // fallback: first block with text
  for (const sp of spBlocks) {
    const text = extractText(sp)
    if (text) return text
  }

  return 'Untitled Slide'
}

/**
 * Extract body content — all text EXCEPT the title placeholder.
 */
function extractBody(xml) {
  const spBlocks = xml.match(/<p:sp[\s\S]*?<\/p:sp>/g) || []
  const lines = []

  for (const sp of spBlocks) {
    // skip title/ctrTitle placeholders
    if (/type="title"|type="ctrTitle"/i.test(sp)) continue
    const text = extractText(sp)
    if (text) lines.push(text)
  }

  return lines.join('\n')
}

/**
 * Main export — call with a File object (.pptx).
 * Returns Promise<{ title: string, slides: Array<{ id, title, content, index }> }>
 */
export async function parsePptx(file) {
  const arrayBuffer = await file.arrayBuffer()
  const zip = await JSZip.loadAsync(arrayBuffer)

  // collect slide XML files in order
  const slideFiles = Object.keys(zip.files)
    .filter(name => /^ppt\/slides\/slide\d+\.xml$/.test(name))
    .sort((a, b) => {
      const numA = parseInt(a.match(/slide(\d+)/)[1])
      const numB = parseInt(b.match(/slide(\d+)/)[1])
      return numA - numB
    })

  // try to get the presentation title from core.xml
  let presTitle = file.name.replace(/\.[^/.]+$/, '')
  try {
    const coreXml = await zip.file('docProps/core.xml')?.async('string')
    if (coreXml) {
      const titleMatch = coreXml.match(/<dc:title[^>]*>([^<]+)<\/dc:title>/)
      if (titleMatch?.[1]?.trim()) presTitle = titleMatch[1].trim()
    }
  } catch (_) {}

  const slides = await Promise.all(
    slideFiles.map(async (path, index) => {
      const xml = await zip.file(path).async('string')
      return {
        id: `slide-${index + 1}`,
        index: index + 1,
        title: extractTitle(xml),
        content: extractBody(xml),
      }
    })
  )

  return { title: presTitle, slides }
}
