import { atom, read, update } from 'claude-code'
import type { Register } from 'claude-code'

import type { ActionFeedback } from '../types'
import { ACTIONS, DONE_BACKGROUND, FAILED_BACKGROUND, FEEDBACK_MS } from './actions'
import {
  CLAUDE_BACKGROUND,
  FALLBACK_COLUMNS,
  TABLE_BUBBLE_MARGIN,
  USER_BACKGROUND,
  bubble,
  bubbleWidth,
  hasTable,
} from './bubble'

const feedback = atom({ plugin: 'my-claude-code-style', key: 'feedback' } as const, null)

export const register: Register = on => {
  // The bubble frames are terminal block glyphs; other surfaces draw them as solid bars.
  on('ui.render', { component: 'AssistantMessage' }, async ($, e, next) => {
    if (e.surface !== 'terminal') {
      return next(e)
    }

    const { Box, Text, Button, Markdown } = $.ui.resolve(e)
    const columns = e.viewport?.columns ?? FALLBACK_COLUMNS
    const width = hasTable(e.props.text)
      ? columns - TABLE_BUBBLE_MARGIN
      : bubbleWidth(e.props.text, columns)
    const shown = await read($, feedback)

    const buttons = ACTIONS.map(action => {
      const state = shown?.messageId === e.requestId && shown.actionId === action.id ? shown : null
      const label = state === null ? action.label : state.isDone ? action.doneLabel : action.failedLabel
      const background =
        state === null ? action.background : state.isDone ? DONE_BACKGROUND : FAILED_BACKGROUND

      return (
        <Button
          key={`${action.id}:${e.requestId}`}
          label={action.label.trim()}
          plain
          onPress={async press => {
            const isDone = await action.run(
              {
                copy: async text => (await $.ui.copy({ text, surface: press.surface })).isCopied,
              },
              { text: e.props.text },
            )
            const result: ActionFeedback = { actionId: action.id, messageId: e.requestId, isDone }
            await update($, feedback, () => result)
            $.clock.after(FEEDBACK_MS, () => update($, feedback, () => null))
          }}
        >
          <Text bold color="#ffffff" backgroundColor={background}>
            {label}
          </Text>
        </Button>
      )
    })

    return (
      <Box flexDirection="column" alignItems="flex-start" marginTop={1}>
        {bubble({ Box, Text }, CLAUDE_BACKGROUND, width, <Markdown text={e.props.text} />)}
        <Box width={width} justifyContent="flex-end" columnGap={1}>
          {buttons}
        </Box>
      </Box>
    )
  })

  on('ui.render', { component: 'UserMessage' }, ($, e, next) => {
    if (e.surface !== 'terminal' || e.props.origin.kind !== 'composer') {
      return next(e)
    }

    const { Box, Text } = $.ui.resolve(e)
    const width = bubbleWidth(e.props.text, e.viewport?.columns ?? FALLBACK_COLUMNS)

    return (
      <Box flexDirection="column" alignItems="flex-end" marginTop={1}>
        {bubble({ Box, Text }, USER_BACKGROUND, width, <Text>{e.props.text}</Text>)}
      </Box>
    )
  })
}
