<script setup>
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { marked } from 'marked'

const jiraId = new URLSearchParams(window.location.search).get('jira_id') || ''
const checkpoint = ref(null)
const loading = ref(true)
const processing = ref(false)
const error = ref(null)
const showRejectForm = ref(false)
const feedback = ref('')
let pollInterval = null

const statusConfig = {
  pending:    { label: 'Awaiting Review',  classes: 'bg-yellow-100 text-yellow-800' },
  processing: { label: 'Processing...',    classes: 'bg-blue-100 text-blue-800' },
  approved:   { label: 'Approved',         classes: 'bg-green-100 text-green-800' },
  rejected:   { label: 'Rejected',         classes: 'bg-red-100 text-red-800' },
}

const statusBadge = computed(() => statusConfig[checkpoint.value?.status] ?? statusConfig.pending)
const renderedSpec = computed(() => checkpoint.value?.spec_doc ? marked.parse(checkpoint.value.spec_doc) : '')

async function fetchCheckpoint() {
  if (!jiraId) { error.value = 'No jira_id provided in URL (?jira_id=TT-1)'; loading.value = false; return }
  try {
    const res = await fetch(`/api/checkpoint/${jiraId}`)
    if (!res.ok) throw new Error('Checkpoint not found')
    checkpoint.value = await res.json()
    if (checkpoint.value.status === 'processing') startPolling()
  } catch (e) {
    error.value = e.message
  } finally {
    loading.value = false
  }
}

function startPolling() {
  processing.value = true
  pollInterval = setInterval(async () => {
    const res = await fetch(`/api/checkpoint/${jiraId}/status`)
    const data = await res.json()
    if (data.status !== 'processing') {
      clearInterval(pollInterval)
      pollInterval = null
      processing.value = false
      await fetchCheckpoint()
    }
  }, 2000)
}

async function approve() {
  processing.value = true
  showRejectForm.value = false
  await fetch(`/api/checkpoint/${jiraId}/approve`, { method: 'POST' })
  startPolling()
}

async function submitReject() {
  if (!feedback.value.trim()) return
  processing.value = true
  showRejectForm.value = false
  await fetch(`/api/checkpoint/${jiraId}/reject`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ feedback: feedback.value }),
  })
  feedback.value = ''
  startPolling()
}

onMounted(fetchCheckpoint)
onUnmounted(() => { if (pollInterval) clearInterval(pollInterval) })
</script>

<template>
  <!-- Loading skeleton -->
  <div v-if="loading" class="min-h-screen flex items-center justify-center bg-gray-50">
    <div class="text-gray-500 text-lg animate-pulse">Loading checkpoint…</div>
  </div>

  <!-- Error state -->
  <div v-else-if="error" class="min-h-screen flex items-center justify-center bg-gray-50">
    <div class="bg-red-50 border border-red-200 rounded-lg p-8 text-center max-w-md">
      <p class="text-red-600 font-medium text-lg">{{ error }}</p>
      <p class="text-red-400 text-sm mt-2">Check that the checkpoint server is running and the jira_id is correct.</p>
    </div>
  </div>

  <!-- Main UI -->
  <div v-else class="min-h-screen bg-gray-50 flex flex-col">

    <!-- Header -->
    <header class="bg-white border-b border-gray-200 px-6 py-4 flex items-center justify-between shadow-sm">
      <div class="flex items-center gap-3">
        <span class="text-xl font-bold text-gray-900">Autopilot</span>
        <span class="text-gray-400">/</span>
        <span class="text-gray-600 font-mono text-sm bg-gray-100 px-2 py-1 rounded">{{ jiraId }}</span>
        <span class="text-gray-500 text-sm">Spec Review</span>
      </div>
      <span :class="['text-xs font-semibold px-3 py-1 rounded-full', statusBadge.classes]">
        {{ statusBadge.label }}
      </span>
    </header>

    <!-- Content -->
    <div class="flex flex-1 overflow-hidden">

      <!-- Left panel: context -->
      <aside class="w-96 bg-white border-r border-gray-200 overflow-y-auto flex-shrink-0 p-5 space-y-6">

        <section>
          <h2 class="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-3">Story</h2>
          <p class="text-gray-700 text-sm leading-relaxed whitespace-pre-wrap">{{ checkpoint.story_text }}</p>
        </section>

        <hr class="border-gray-100" />

        <section>
          <h2 class="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-3">
            Acceptance Criteria
          </h2>
          <ul class="space-y-2">
            <li
              v-for="(ac, i) in checkpoint.acceptance_criteria"
              :key="i"
              class="flex gap-2 text-sm text-gray-700"
            >
              <span class="mt-0.5 text-green-500 flex-shrink-0">✓</span>
              <span>{{ ac }}</span>
            </li>
          </ul>
        </section>

        <hr class="border-gray-100" />

        <section>
          <h2 class="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-3">
            Technical Details
          </h2>
          <ul class="space-y-2">
            <li
              v-for="(td, i) in checkpoint.tech_details"
              :key="i"
              class="text-sm text-gray-700 bg-gray-50 rounded px-3 py-2"
            >
              {{ td }}
            </li>
          </ul>
        </section>

        <section v-if="checkpoint.feedback">
          <hr class="border-gray-100 mb-6" />
          <h2 class="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-3">
            Previous Feedback
          </h2>
          <p class="text-sm text-red-700 bg-red-50 border border-red-100 rounded px-3 py-2 leading-relaxed">
            {{ checkpoint.feedback }}
          </p>
        </section>

      </aside>

      <!-- Right panel: spec -->
      <main class="flex-1 overflow-y-auto p-8">
        <h2 class="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-4">Generated Spec</h2>
        <div
          class="prose prose-sm max-w-none bg-white rounded-lg border border-gray-200 p-6 shadow-sm"
          v-html="renderedSpec"
        />
      </main>
    </div>

    <!-- Action bar -->
    <footer class="bg-white border-t border-gray-200 px-6 py-4">

      <!-- Processing loader -->
      <div v-if="processing" class="flex items-center gap-3 text-blue-600">
        <svg class="animate-spin h-5 w-5" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
          <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
          <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z"/>
        </svg>
        <span class="text-sm font-medium">Agent is running… please wait</span>
      </div>

      <!-- Approved final state -->
      <div v-else-if="checkpoint.status === 'approved'" class="flex items-center gap-2 text-green-600">
        <span class="text-lg">✅</span>
        <span class="text-sm font-medium">Spec approved. Step 4 (Dev Agent) is starting.</span>
      </div>

      <!-- Pending: approve / reject actions -->
      <div v-else-if="checkpoint.status === 'pending'" class="space-y-3">
        <div v-if="!showRejectForm" class="flex gap-3">
          <button
            @click="approve"
            class="px-5 py-2 bg-green-600 hover:bg-green-700 text-white text-sm font-medium rounded-lg transition-colors"
          >
            ✅ Approve Spec
          </button>
          <button
            @click="showRejectForm = true"
            class="px-5 py-2 bg-red-50 hover:bg-red-100 text-red-700 text-sm font-medium rounded-lg border border-red-200 transition-colors"
          >
            ❌ Reject & Revise
          </button>
        </div>

        <!-- Reject form -->
        <div v-else class="flex flex-col gap-2 max-w-2xl">
          <label class="text-sm font-medium text-gray-700">
            What should be changed? <span class="text-red-500">*</span>
          </label>
          <textarea
            v-model="feedback"
            rows="3"
            placeholder="Describe what needs to be revised in the spec…"
            class="border border-gray-300 rounded-lg px-3 py-2 text-sm resize-none focus:outline-none focus:ring-2 focus:ring-red-400"
          />
          <div class="flex gap-2">
            <button
              @click="submitReject"
              :disabled="!feedback.trim()"
              class="px-4 py-2 bg-red-600 hover:bg-red-700 disabled:opacity-40 disabled:cursor-not-allowed text-white text-sm font-medium rounded-lg transition-colors"
            >
              Submit & Re-run Prep
            </button>
            <button
              @click="showRejectForm = false; feedback = ''"
              class="px-4 py-2 text-gray-600 hover:text-gray-900 text-sm font-medium"
            >
              Cancel
            </button>
          </div>
        </div>
      </div>

      <!-- Rejected: waiting for re-run result -->
      <div v-else-if="checkpoint.status === 'rejected'" class="text-sm text-gray-500">
        Feedback submitted. Refresh after the prep agent completes.
      </div>

    </footer>
  </div>
</template>
