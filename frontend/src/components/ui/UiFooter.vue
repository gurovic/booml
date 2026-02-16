<template>
  <footer class="footer">
    <div class="container footer__inner">
      <div class="footer__brand">
        <span class="footer__brand-name">BOOML</span>
        <span class="footer__brand-note">© 2026. Все права защищены</span>
      </div>
      <div class="footer__contacts">
        <a class="footer__link" href="mailto:booml@letovo.ru">booml@letovo.ru</a>
        <a
          class="footer__icon-link"
          href="https://t.me/booml_letovo"
          target="_blank"
          rel="noopener noreferrer"
          aria-label="Telegram канал BOOML"
        >
          <svg class="footer__icon" viewBox="0 0 24 24" aria-hidden="true">
            <path
              d="M22 4.01a1 1 0 0 0-1.08-.17L2.7 11.1a1 1 0 0 0 .08 1.87l4.75 1.58 1.98 5.88a1 1 0 0 0 1.7.39l2.74-2.73 4.77 3.5a1 1 0 0 0 1.57-.6L23 5.02a1 1 0 0 0-1-1.01ZM9.86 15.1l-.82 2.44-1.25-3.72 8.37-6.2-6.3 7.48Z"
            />
          </svg>
        </a>
      </div>
    </div>
  </footer>
</template>

<script setup>
</script>

<style scoped>
.footer {
  background-color: var(--color-primary);
  border-top: 1px solid rgba(255, 255, 255, 0.12);
  padding: 18px 0;
  font-size: 14px;
}

.footer__inner {
  display: flex;
  flex-wrap: wrap;
  gap: 10px 24px;
  align-items: center;
  justify-content: space-between;
}

.footer__brand {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
  color: #ffffff;
}

.footer__brand-name {
  font-family: var(--font-title);
  font-size: 16px;
  letter-spacing: 0.04em;
}

.footer__brand-note {
  opacity: 0.85;
}

.footer__link {
  color: #ffffff;
  font-weight: 500;
  transition: opacity 0.2s ease;
}

.footer__link:hover {
  opacity: 0.8;
}

.footer__contacts {
  display: flex;
  align-items: center;
  gap: 14px;
}

.footer__icon-link {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border-radius: 8px;
  border: 1px solid rgba(255, 255, 255, 0.25);
  transition: opacity 0.2s ease, border-color 0.2s ease;
}

.footer__icon-link:hover {
  opacity: 0.85;
  border-color: rgba(255, 255, 255, 0.5);
}

.footer__icon {
  width: 18px;
  height: 18px;
  fill: currentColor;
  color: #ffffff;
}

@media (max-width: 640px) {
  .footer__inner {
    justify-content: center;
    text-align: center;
  }
}
</style>
