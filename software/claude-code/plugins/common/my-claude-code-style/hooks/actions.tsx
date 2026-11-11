// What an action may do. register.tsx builds one of these per press, because
// only a hook may hold the engine interface.
export type ActionContext = {
  copy: (text: string) => Promise<boolean>
}

export type Action = {
  id: string
  label: string
  doneLabel: string
  failedLabel: string
  background: string
  run: (context: ActionContext, message: { text: string }) => Promise<boolean>
}

export const DONE_BACKGROUND = '#2f855a'
export const FAILED_BACKGROUND = '#b83232'
export const FEEDBACK_MS = 1500

// Buttons under each Claude message, left to right. To add one, add an entry.
export const ACTIONS: Action[] = [
  {
    id: 'copy',
    label: ' Copy ',
    doneLabel: ' ✓ Copied ',
    failedLabel: ' Failed ',
    background: '#6b7a99',
    run: (context, message) => context.copy(message.text),
  },
]
