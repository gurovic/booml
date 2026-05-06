<template>
    <div class="turnstile-captcha">
        <div ref="containerRef"></div>
    </div>
</template>

<script setup>
import { onBeforeUnmount, onMounted, ref } from 'vue'

const props = defineProps({
    modelValue: {
        type: String,
        default: '',
    },
    siteKey: {
        type: String,
        required: true,
    },
})

const emit = defineEmits(['update:modelValue', 'load-error'])

const containerRef = ref(null)
let widgetId = null
let turnstileScriptPromise = null

const loadTurnstileScript = () => {
    if (window.turnstile?.render) {
        return Promise.resolve(window.turnstile)
    }

    if (turnstileScriptPromise) {
        return turnstileScriptPromise
    }

    turnstileScriptPromise = new Promise((resolve, reject) => {
        const existing = document.querySelector('script[data-turnstile-script="true"]')

        if (existing) {
            existing.addEventListener('load', () => resolve(window.turnstile), { once: true })
            existing.addEventListener('error', () => reject(new Error('Failed to load Turnstile')), { once: true })
            return
        }

        const script = document.createElement('script')
        script.src = 'https://challenges.cloudflare.com/turnstile/v0/api.js?render=explicit'
        script.async = true
        script.defer = true
        script.dataset.turnstileScript = 'true'
        script.onload = () => resolve(window.turnstile)
        script.onerror = () => reject(new Error('Failed to load Turnstile'))
        document.head.appendChild(script)
    })

    return turnstileScriptPromise
}

const renderWidget = async () => {
    try {
        const turnstile = await loadTurnstileScript()

        if (!containerRef.value || !turnstile?.render) {
            throw new Error('Turnstile is unavailable')
        }

        widgetId = turnstile.render(containerRef.value, {
            sitekey: props.siteKey,
            callback: (token) => emit('update:modelValue', token),
            'expired-callback': () => emit('update:modelValue', ''),
            'error-callback': () => emit('update:modelValue', ''),
        })
    } catch (error) {
        emit('load-error', error)
    }
}

const reset = () => {
    emit('update:modelValue', '')
    if (widgetId != null && window.turnstile?.reset) {
        window.turnstile.reset(widgetId)
    }
}

defineExpose({ reset })

onMounted(() => {
    renderWidget()
})

onBeforeUnmount(() => {
    if (widgetId != null && window.turnstile?.remove) {
        window.turnstile.remove(widgetId)
    }
})
</script>

<style scoped>
.turnstile-captcha {
    width: 100%;
}
</style>
