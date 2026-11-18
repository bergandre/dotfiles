import type { ThemeSetArgs } from 'claude-code'

import { makeColors } from './make-colors.js'

export type Variant = 'dungeon' | 'profession'

// Dungeon: a cave lit by a cyan glow, framed by loading-screen parchment.
// Light mode is the parchment frame, dark mode the cave itself.
const dungeon = makeColors({
  label: 'WoW Dungeon',
  roles: { accent: '#2f9fa3', danger: '#b8452f', success: '#6d8f3a', warning: '#b07a24', pro: '#7a5aa6' },
  light: {
    gray: {
      anchors: {
        'surface-0': '#e3d2ad',
        'surface-1': '#eadbb9',
        'surface-2': '#f1e5c9',
        'text-primary': '#2b2114',
        'text-secondary': '#4e3f29',
        'text-muted': '#655238',
      },
    },
  },
  dark: {
    gray: {
      anchors: {
        'surface-0': '#17160f',
        'surface-1': '#1f1d14',
        'surface-2': '#27241a',
        'surface-3': '#2e2a1f',
        'text-primary': '#ecdfc2',
        'text-secondary': '#cdbf9f',
        'text-muted': '#a99b7c',
      },
    },
  },
})

// Profession: a forge at night. Soot, glowing iron, gold, steel.
const profession = makeColors({
  label: 'WoW Profession',
  only: 'dark',
  roles: { accent: '#ff7a1a', danger: '#e2412f', success: '#7fb04a', warning: '#f0b030', pro: '#9a6ad8' },
  dark: {
    gray: {
      anchors: {
        'surface-0': '#110d0b',
        'surface-1': '#1a1411',
        'surface-2': '#221a16',
        'surface-3': '#29201b',
        'text-primary': '#f4eadd',
        'text-secondary': '#d6c8b8',
        'text-muted': '#ab9d8f',
      },
    },
  },
})

export const PROBLEMS: Record<Variant, string[]> = {
  dungeon: dungeon.problems,
  profession: profession.problems,
}

export const LOOKS: Record<Variant, ThemeSetArgs> = {
  dungeon: {
    colors: dungeon.theme,
    // The cave's glow behind the conversation, fading into the dark.
    backdrop: {
      gradient: {
        shape: 'radial',
        stops: [
          { at: 0, color: 'surface-2' },
          { at: 1, color: 'surface-0' },
        ],
      },
    },
  },
  profession: {
    colors: profession.theme,
    overrideColorScheme: 'dark',
    // Embers rising from the bottom of the window.
    backdrop: {
      gradient: {
        angle: 0,
        stops: [
          { at: 0, color: '#3a1606' },
          { at: 0.45, color: '#110d0b' },
          { at: 1, color: '#110d0b' },
        ],
      },
    },
  },
}

// The band above the prompt, drawn in the terminal too.
export const BAND: Record<Variant, { icon: string; label: string; color: string; hint: string }> = {
  dungeon: { icon: '⚔', label: 'Dungeon session', color: '#6fe3e0', hint: 'quests · tactics · loot' },
  profession: { icon: '⚒', label: 'Profession session', color: '#ff8a2a', hint: 'skills · mats · AH' },
}
