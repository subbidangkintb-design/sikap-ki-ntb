const KNOWN_HEADINGS = new Set([
  'jawaban singkat',
  'penjelasan',
  'rincian',
  'persyaratan',
  'langkah berikutnya',
  'ringkasan hasil',
  'ringkasan indikator',
  'hal yang perlu ditinjau',
  'penyesuaian label yang perlu ditinjau',
])

export default function FormattedResponse({ text, className = '' }) {
  const blocks = parseBlocks(text)

  return (
    <div className={`response-content ${className}`.trim()}>
      {blocks.map((block, index) => {
        if (block.type === 'heading') {
          return <h3 key={`${block.type}-${index}`}>{renderInline(block.text)}</h3>
        }
        if (block.type === 'ul' || block.type === 'ol') {
          const ListTag = block.type
          return (
            <ListTag key={`${block.type}-${index}`}>
              {block.items.map((item, itemIndex) => <li key={`${item}-${itemIndex}`}>{renderInline(item)}</li>)}
            </ListTag>
          )
        }
        return <p key={`${block.type}-${index}`}>{renderInline(block.text)}</p>
      })}
    </div>
  )
}

function parseBlocks(value) {
  const lines = String(value || '').replace(/\r\n/g, '\n').split('\n')
  const blocks = []
  let paragraph = []
  let list = null

  function flushParagraph() {
    if (!paragraph.length) return
    blocks.push({ type: 'paragraph', text: paragraph.join(' ').trim() })
    paragraph = []
  }

  function flushList() {
    if (!list) return
    blocks.push(list)
    list = null
  }

  for (const rawLine of lines) {
    const line = rawLine.trim()
    if (!line) {
      flushParagraph()
      flushList()
      continue
    }

    const heading = getHeading(line)
    if (heading) {
      flushParagraph()
      flushList()
      blocks.push({ type: 'heading', text: heading })
      continue
    }

    const unordered = line.match(/^(?:[-*•])\s+(.+)$/)
    const ordered = line.match(/^\d+[.)]\s+(.+)$/)
    if (unordered || ordered) {
      flushParagraph()
      const type = ordered ? 'ol' : 'ul'
      if (list?.type !== type) flushList()
      if (!list) list = { type, items: [] }
      list.items.push((ordered || unordered)[1].trim())
      continue
    }

    flushList()
    paragraph.push(line)
  }

  flushParagraph()
  flushList()
  return blocks
}

function getHeading(line) {
  const markdownHeading = line.match(/^#{1,4}\s+(.+)$/)
  if (markdownHeading) return markdownHeading[1].replace(/\*\*/g, '').replace(/:$/, '').trim()

  const boldHeading = line.match(/^\*\*([^*]+?)\*\*:?$/)
  if (boldHeading) return boldHeading[1].replace(/:$/, '').trim()

  const plain = line.replace(/:$/, '').trim()
  return KNOWN_HEADINGS.has(plain.toLowerCase()) ? plain : null
}

function renderInline(text) {
  return String(text).split(/(\*\*[^*]+\*\*|\*[^*]+\*|`[^`]+`|https?:\/\/[^\s]+|www\.[^\s]+)/g).filter(Boolean).map((part, index) => {
    if (part.startsWith('**') && part.endsWith('**')) {
      return <strong key={`${part}-${index}`}>{part.slice(2, -2)}</strong>
    }
    if (part.startsWith('*') && part.endsWith('*')) {
      return <em key={`${part}-${index}`}>{part.slice(1, -1)}</em>
    }
    if (part.startsWith('`') && part.endsWith('`')) {
      return <code key={`${part}-${index}`}>{part.slice(1, -1)}</code>
    }
    if (part.startsWith('http://') || part.startsWith('https://') || part.startsWith('www.')) {
      const punctuation = part.match(/[.,;:)]$/)?.[0] || ''
      const label = punctuation ? part.slice(0, -1) : part
      const href = label.startsWith('www.') ? `https://${label}` : label
      return <span key={`${part}-${index}`}><a href={href} target="_blank" rel="noreferrer">{label}</a>{punctuation}</span>
    }
    return part
  })
}
