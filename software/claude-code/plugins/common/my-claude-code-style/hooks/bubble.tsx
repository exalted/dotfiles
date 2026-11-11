export const CLAUDE_BACKGROUND = '#363f50'
export const USER_BACKGROUND = '#5b21b6'
export const FALLBACK_COLUMNS = 100
export const TABLE_BUBBLE_MARGIN = 1

const MAX_WIDTH_SHARE = 0.9
const PADDING_X = 2
const PADDING = PADDING_X * 2
const CORNER_COLUMNS = 2

export type Elements = { Box: any; Text: any }

// The engine draws a markdown table to the terminal's width, not to its
// container's, so a bubble holding one spans the terminal or the table breaks.
export const hasTable = (text: string) => /^\s*\|.*\|\s*$/m.test(text)

// The frame rows cannot measure the body, so the bubble gets one explicit
// width, from the widest source line, capped at a share of the terminal. The
// width follows the terminal because a resize redraws every row.
export const bubbleWidth = (text: string, columns: number) => {
  const cap = Math.floor(columns * MAX_WIDTH_SHARE)
  const widest = Math.max(1, ...text.split('\n').map(line => line.length))

  return Math.min(cap, widest + PADDING)
}

// Only the first and last row of a bubble hold glyphs; the rows between hold
// plain spaces, so selecting the text copies no frame characters.
const edge = (
  { Box, Text }: Elements,
  color: string,
  width: number,
  left: string,
  fill: string,
  right: string,
) => (
  <Box flexDirection="row" width={width}>
    <Text color={color}>{left}</Text>
    <Box width={width - CORNER_COLUMNS} height={1} overflow="hidden">
      <Text color={color}>{fill.repeat(Math.max(0, width - CORNER_COLUMNS))}</Text>
    </Box>
    <Text color={color}>{right}</Text>
  </Box>
)

export const bubble = (elements: Elements, color: string, width: number, body: unknown) => {
  const { Box } = elements

  return (
    <Box flexDirection="column" width={width}>
      {edge(elements, color, width, '▗', '▄', '▖')}
      <Box backgroundColor={color} paddingX={PADDING_X} width={width}>
        {body}
      </Box>
      {edge(elements, color, width, '▝', '▀', '▘')}
    </Box>
  )
}
