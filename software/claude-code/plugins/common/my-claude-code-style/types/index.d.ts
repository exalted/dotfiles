export type ActionFeedback = { actionId: string; messageId: string; isDone: boolean }

declare module 'claude-code' {
  interface PluginState {
    'my-claude-code-style': { feedback: ActionFeedback | null }
  }
}
