<template>
  <div class="flex min-h-screen bg-surface-950">

    <!-- Global subtle page glow -->
    <div class="fixed inset-0 bg-page-glow pointer-events-none z-0"></div>
    <!-- Dot grid texture -->
    <div class="fixed inset-0 bg-dot-grid pointer-events-none z-0 opacity-60"></div>

    <!-- ── Sidebar ─────────────────────────────────────────── -->
    <aside class="w-60 bg-surface-950/95 border-r border-surface-800/40 flex flex-col fixed h-full z-30">
      <!-- Sidebar ambient glow -->
      <div class="absolute top-0 left-0 right-0 h-72 bg-sidebar-glow pointer-events-none"></div>

      <!-- Logo -->
      <div class="relative px-5 pt-6 pb-5 border-b border-surface-800/40">
        <div class="flex items-center gap-3">
          <!-- Forge mark -->
          <div class="w-9 h-9 rounded-xl bg-gradient-to-br from-forge-500 to-forge-700 flex items-center justify-center shadow-ember shrink-0 relative">
            <svg class="w-5 h-5 text-white" viewBox="0 0 20 20" fill="currentColor">
              <path d="M10.5 2.5L5 11h4.5L9 17.5l6-9.5h-4.5l1.5-5.5h-1.5z"/>
            </svg>
            <div class="absolute inset-0 rounded-xl ring-1 ring-white/10"></div>
          </div>
          <div>
            <div class="text-[15px] font-bold text-white tracking-tight leading-none">SimForge</div>
            <div class="text-[10px] font-semibold text-surface-500 tracking-widest uppercase mt-1">Platform</div>
          </div>
        </div>
      </div>

      <!-- Navigation -->
      <nav class="relative flex-1 px-3 py-3 space-y-0.5 overflow-y-auto">
        <NuxtLink
          v-for="item in navItems"
          :key="item.path"
          :to="item.path"
          :class="$route.path === item.path ? 'nav-link-active' : 'nav-link'"
        >
          <component :is="item.icon" class="w-4 h-4 shrink-0" />
          <span class="flex-1 truncate">{{ item.label }}</span>
          <span
            v-if="item.badge"
            class="text-[9px] px-1.5 py-0.5 rounded-full bg-forge-600/25 text-forge-300 font-bold tracking-wider uppercase"
          >
            {{ item.badge }}
          </span>
        </NuxtLink>
      </nav>

      <!-- Footer -->
      <div class="px-4 py-4 border-t border-surface-800/40 relative">
        <div class="flex items-center gap-2.5">
          <div class="w-1.5 h-1.5 rounded-full bg-success animate-pulse-slow"></div>
          <span class="text-xs text-surface-500">Mock Provider</span>
          <span class="ml-auto text-[10px] text-surface-600 font-mono">v0.1.0</span>
        </div>
      </div>
    </aside>

    <!-- ── Main area ───────────────────────────────────────── -->
    <main class="relative flex-1 ml-60 flex flex-col min-h-screen">

      <!-- Top header -->
      <header class="sticky top-0 z-20 bg-surface-950/90 backdrop-blur-xl border-b border-surface-800/30 px-8 h-16 flex items-center gap-4">
        <div class="flex-1 min-w-0">
          <h2 class="page-title leading-none">{{ pageTitle }}</h2>
          <p v-if="pageSubtitle" class="text-xs text-surface-500 mt-1 leading-none truncate">{{ pageSubtitle }}</p>
        </div>
        <div class="flex items-center gap-2">
          <div class="flex items-center gap-2 px-3 py-1.5 rounded-full bg-surface-900 border border-surface-800/60 text-xs text-surface-400 select-none">
            <div class="w-1.5 h-1.5 rounded-full bg-success"></div>
            <span>API Connected</span>
          </div>
        </div>
      </header>

      <!-- Page content -->
      <div class="flex-1 p-8">
        <slot />
      </div>
    </main>

  </div>
</template>

<script setup lang="ts">
import { h, defineComponent } from 'vue'

const route = useRoute()

function SvgIcon(d: string) {
  return defineComponent({
    render: () =>
      h('svg', { fill: 'none', viewBox: '0 0 24 24', stroke: 'currentColor', 'stroke-width': '1.6' },
        [h('path', { 'stroke-linecap': 'round', 'stroke-linejoin': 'round', d })]),
  })
}

const navItems = [
  {
    path: '/',
    label: 'Overview',
    icon: SvgIcon('M3.75 6A2.25 2.25 0 016 3.75h2.25A2.25 2.25 0 0110.5 6v2.25a2.25 2.25 0 01-2.25 2.25H6a2.25 2.25 0 01-2.25-2.25V6zM3.75 15.75A2.25 2.25 0 016 13.5h2.25a2.25 2.25 0 012.25 2.25V18a2.25 2.25 0 01-2.25 2.25H6A2.25 2.25 0 013.75 18v-2.25zM13.5 6a2.25 2.25 0 012.25-2.25H18A2.25 2.25 0 0120.25 6v2.25A2.25 2.25 0 0118 10.5h-2.25a2.25 2.25 0 01-2.25-2.25V6zM13.5 15.75a2.25 2.25 0 012.25-2.25H18a2.25 2.25 0 012.25 2.25V18A2.25 2.25 0 0118 20.25h-2.25A2.25 2.25 0 0113.5 18v-2.25z'),
  },
  {
    path: '/scenarios',
    label: 'Scenarios',
    icon: SvgIcon('M9 12h3.75M9 15h3.75M9 18h3.75m3 .75H18a2.25 2.25 0 002.25-2.25V6.108c0-1.135-.845-2.098-1.976-2.192a48.424 48.424 0 00-1.123-.08m-5.801 0c-.065.21-.1.433-.1.664 0 .414.336.75.75.75h4.5a.75.75 0 00.75-.75 2.25 2.25 0 00-.1-.664m-5.8 0A2.251 2.251 0 0113.5 2.25H15c1.012 0 1.867.668 2.15 1.586m-5.8 0c-.376.023-.75.05-1.124.08C9.095 4.01 8.25 4.973 8.25 6.108V8.25m0 0H4.875c-.621 0-1.125.504-1.125 1.125v11.25c0 .621.504 1.125 1.125 1.125h9.75c.621 0 1.125-.504 1.125-1.125V9.375c0-.621-.504-1.125-1.125-1.125H8.25z'),
  },
  {
    path: '/builder',
    label: 'Builder',
    icon: SvgIcon('M12 9v6m3-3H9m12 0a9 9 0 11-18 0 9 9 0 0118 0z'),
    badge: 'New',
  },
  {
    path: '/runs',
    label: 'Runs',
    icon: SvgIcon('M5.25 5.653c0-.856.917-1.398 1.667-.986l11.54 6.348a1.125 1.125 0 010 1.971l-11.54 6.347a1.125 1.125 0 01-1.667-.985V5.653z'),
  },
  {
    path: '/outputs',
    label: 'Outputs',
    icon: SvgIcon('M2.25 15.75l5.159-5.159a2.25 2.25 0 013.182 0l5.159 5.159m-1.5-1.5l1.409-1.409a2.25 2.25 0 013.182 0l2.909 2.909M3.75 21h16.5A2.25 2.25 0 0022.5 18.75V5.25A2.25 2.25 0 0020.25 3H3.75A2.25 2.25 0 001.5 5.25v13.5A2.25 2.25 0 003.75 21z'),
  },
  {
    path: '/evaluation',
    label: 'Evaluation',
    icon: SvgIcon('M3 13.125C3 12.504 3.504 12 4.125 12h2.25c.621 0 1.125.504 1.125 1.125v6.75C7.5 20.496 6.996 21 6.375 21h-2.25A1.125 1.125 0 013 19.875v-6.75zM9.75 8.625c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125v11.25c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V8.625zM16.5 4.125c0-.621.504-1.125 1.125-1.125h2.25C20.496 3 21 3.504 21 4.125v15.75c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V4.125z'),
  },
  {
    path: '/activity',
    label: 'Activity',
    icon: SvgIcon('M12 6v6h4.5m4.5 0a9 9 0 11-18 0 9 9 0 0118 0z'),
  },
  {
    path: '/settings',
    label: 'Settings',
    icon: SvgIcon('M9.594 3.94c.09-.542.56-.94 1.11-.94h2.593c.55 0 1.02.398 1.11.94l.213 1.281c.063.374.313.686.645.87.074.04.147.083.22.127.324.196.72.257 1.075.124l1.217-.456a1.125 1.125 0 011.37.49l1.296 2.247a1.125 1.125 0 01-.26 1.431l-1.003.827c-.293.24-.438.613-.431.992a6.759 6.759 0 010 .255c-.007.378.138.75.43.99l1.005.828c.424.35.534.954.26 1.43l-1.298 2.247a1.125 1.125 0 01-1.369.491l-1.217-.456c-.355-.133-.75-.072-1.076.124a6.57 6.57 0 01-.22.128c-.331.183-.581.495-.644.869l-.213 1.28c-.09.543-.56.941-1.11.941h-2.594c-.55 0-1.02-.398-1.11-.94l-.213-1.281c-.062-.374-.312-.686-.644-.87a6.52 6.52 0 01-.22-.127c-.325-.196-.72-.257-1.076-.124l-1.217.456a1.125 1.125 0 01-1.369-.49l-1.297-2.247a1.125 1.125 0 01.26-1.431l1.004-.827c.292-.24.437-.613.43-.992a6.932 6.932 0 010-.255c.007-.378-.138-.75-.43-.99l-1.004-.828a1.125 1.125 0 01-.26-1.43l1.297-2.247a1.125 1.125 0 011.37-.491l1.216.456c.356.133.751.072 1.076-.124.072-.044.146-.087.22-.128.332-.183.582-.495.644-.869l.214-1.281zM15 12a3 3 0 11-6 0 3 3 0 016 0z'),
  },
]

const pageTitles: Record<string, { title: string; subtitle?: string }> = {
  '/':           { title: 'Overview',          subtitle: 'Simulation platform health and recent activity' },
  '/scenarios':  { title: 'Scenarios',          subtitle: 'Manage warehouse edge-case scenario definitions' },
  '/builder':    { title: 'Scenario Builder',   subtitle: 'Define and configure a new simulation scenario' },
  '/runs':       { title: 'Simulation Runs',    subtitle: 'Monitor and manage active simulation jobs' },
  '/outputs':    { title: 'Outputs',            subtitle: 'Browse simulation artifacts and generated media' },
  '/evaluation': { title: 'Evaluation',         subtitle: 'Analyze risk scores and coverage metrics' },
  '/activity':   { title: 'Activity',           subtitle: 'System events and operation timeline' },
  '/settings':   { title: 'Settings',           subtitle: 'Platform configuration and provider settings' },
}

const pageTitle    = computed(() => pageTitles[route.path]?.title    ?? 'SimForge')
const pageSubtitle = computed(() => pageTitles[route.path]?.subtitle ?? '')
</script>
