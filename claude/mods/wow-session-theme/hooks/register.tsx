import type { Register } from 'claude-code'

import { BAND, LOOKS, PROBLEMS } from './looks'
import type { Variant } from './looks'

// The session's variant comes from its terminal theme (`custom:wow-dungeon` /
// `custom:wow-profession`, set per session with `claude --settings`), so the
// terminal colours, the band and the desktop look always agree.
function variantOf(theme: unknown): Variant | undefined {
  const value = String(theme ?? '')

  if (value.includes('wow-dungeon')) {
    return 'dungeon'
  }
  if (value.includes('wow-profession')) {
    return 'profession'
  }

  return undefined
}

export const register: Register = on => {
  let variant: Variant | undefined

  on('session.start', async ($, e, next) => {
    const row = (await $.config.list()).find(one => one.key === 'theme')
    variant = variantOf(row?.value)

    if (variant !== undefined) {
      const unpainted = PROBLEMS[variant].find(line => line.startsWith("Desktop won't paint"))

      if (unpainted !== undefined) {
        $.ui.toast(unpainted)
      }
      await $.theme.set(LOOKS[variant])
    }

    return next(e)
  })

  on('ui.render', { component: 'AbovePrompt' }, ($, e, next) => {
    if (variant === undefined || e.props.hasSurvey) {
      return next(e)
    }

    const { Box, Text } = $.ui.resolve(e)
    const band = BAND[variant]

    return (
      <Box>
        <Text color={band.color} bold>
          {band.icon} {band.label}
        </Text>
        <Text dimColor> · {band.hint}</Text>
      </Box>
    )
  })
}
