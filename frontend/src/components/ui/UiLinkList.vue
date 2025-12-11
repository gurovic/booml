<template>
  <div class="menu-list">
    <h1>{{ title }}</h1>

    <ul>
      <li v-for="item in items" :key="item.text">
        <router-link :to="item.route">
          {{ item.text }}
        </router-link>
      </li>
    </ul>
  </div>
</template>

<script>
export default {
  name: "MenuList",
  props: {
    title: {
      type: String,
      required: true
    },
    items: {
      type: Array,
      required: true
    }
  }
}
</script>
