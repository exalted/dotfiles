import { expect, test } from 'claude-code/testing'

const PLUGIN = 'my-claude-code-style'
const ASSISTANT = { text: 'Hello', isFirstOfReply: true } as const
const USER = { text: 'Hi', origin: { kind: 'composer' }, isExpanded: false } as const

// The bubble frames are terminal block glyphs: the desktop app drew them as solid bars.
for (const surface of ['desktop', 'vscode', 'mobile'] as const) {
  test(`${surface} draws its own assistant message`, async $ => {
    const ui = await $.ui.mount({ plugin: PLUGIN, surface, component: 'AssistantMessage', props: ASSISTANT })
    expect(await ui.keepsBeneath()).toBe(true)
    await ui.unmount()
  })

  test(`${surface} draws its own user message`, async $ => {
    const ui = await $.ui.mount({ plugin: PLUGIN, surface, component: 'UserMessage', props: USER })
    expect(await ui.keepsBeneath()).toBe(true)
    await ui.unmount()
  })
}

test('the terminal draws the assistant bubble', async $ => {
  const ui = await $.ui.mount({ plugin: PLUGIN, surface: 'terminal', component: 'AssistantMessage', props: ASSISTANT })
  expect(await ui.keepsBeneath()).toBe(false)
  expect(await ui.find({ type: 'Button' })).toBeDefined()
  await ui.unmount()
})

test('the terminal draws the user bubble', async $ => {
  const ui = await $.ui.mount({ plugin: PLUGIN, surface: 'terminal', component: 'UserMessage', props: USER })
  expect(await ui.keepsBeneath()).toBe(false)
  await ui.unmount()
})
