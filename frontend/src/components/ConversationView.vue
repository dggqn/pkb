<script setup lang="ts">
import { nextTick, ref } from 'vue'

type Source = { note_id: string; content: string }
type Message = { id: number; role: 'user' | 'assistant'; content: string; sources?: Source[] }

const prompts = ['最近关于灵感的记录', '我对长期主义有哪些想法？', '帮我梳理一个问题']
const messages = ref<Message[]>([])
const question = ref('')
const loading = ref(false)
const error = ref('')
const retryQuestion = ref('')
const thread = ref<HTMLElement | null>(null)
const apiBase = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8001'

async function ask(value = question.value) {
  const text = value.trim()
  if (!text || loading.value) return
  question.value = ''
  error.value = ''
  retryQuestion.value = ''
  messages.value.push({ id: Date.now(), role: 'user', content: text })
  loading.value = true
  await scrollToBottom()
  try {
    const response = await fetch(`${apiBase}/query`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question: text }),
    })
    const payload = await response.json()
    if (!response.ok) throw new Error(payload.detail || `请求失败（${response.status}）`)
    messages.value.push({ id: Date.now() + 1, role: 'assistant', content: payload.answer, sources: payload.sources })
  } catch (reason) {
    error.value = reason instanceof Error ? reason.message : '无法连接后端，请确认 API 服务已启动。'
    // 保留失败的问题，用户能看见刚才发了什么，也可以明确重试。
    retryQuestion.value = text
  } finally {
    loading.value = false
    await scrollToBottom()
  }
}

function retryLastRequest() {
  const text = retryQuestion.value
  if (!text) return

  // 重试前移除失败时留下的问题气泡；ask 会重新添加一次，避免界面出现重复问题。
  const lastMessage = messages.value.at(-1)
  if (lastMessage?.role === 'user' && lastMessage.content === text) {
    messages.value.pop()
  }
  void ask(text)
}

async function scrollToBottom() {
  await nextTick()
  if (thread.value) thread.value.scrollTop = thread.value.scrollHeight
}
</script>

<template>
  <main class="conversation">
    <section ref="thread" class="thread" aria-live="polite">
      <div v-if="!messages.length" class="welcome">
        <span class="welcome-mark" aria-hidden="true">知</span>
        <h1>想从哪件事开始？</h1>
        <p>和你的知识库聊聊。我会从已有记录中寻找线索。</p>
        <div class="suggestions" aria-label="试试这样提问">
          <button v-for="prompt in prompts" :key="prompt" @click="ask(prompt)">{{ prompt }}<span aria-hidden="true">↗</span></button>
        </div>
      </div>
      <article v-for="message in messages" :key="message.id" class="message" :class="`message-${message.role}`">
        <div v-if="message.role === 'assistant'" class="assistant-mark" aria-hidden="true">知</div>
        <div class="message-body">
          <div class="message-label">{{ message.role === 'user' ? '你' : '知间' }}</div>
          <p>{{ message.content }}</p>
          <details v-if="message.sources?.length" class="source-list">
            <summary>参考了 {{ message.sources.length }} 条记录</summary>
            <blockquote v-for="source in message.sources" :key="source.note_id">{{ source.content }}</blockquote>
          </details>
        </div>
      </article>
      <div v-if="loading" class="message message-assistant loading-message"><div class="assistant-mark">知</div><div><div class="message-label">知间</div><p>正在翻阅相关记录<span class="typing-dots">···</span></p></div></div>
      <div v-if="error" class="request-error" role="alert">{{ error }}<button @click="retryLastRequest">重试</button></div>
    </section>
    <form class="composer" @submit.prevent="ask()">
      <textarea v-model="question" :disabled="loading" rows="1" placeholder="给知间发送消息" aria-label="给知间发送消息" @keydown.enter.exact.prevent="ask()" />
      <div class="composer-bottom"><span>Enter 发送 · Shift + Enter 换行</span><button type="submit" :disabled="!question.trim() || loading" aria-label="发送消息"><svg viewBox="0 0 24 24"><path d="M12 19V5m-6 6 6-6 6 6" /></svg></button></div>
    </form>
    <p class="disclaimer">回答基于当前知识库记录，可能不完整。</p>
  </main>
</template>
