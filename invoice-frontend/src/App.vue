<template>
  <div id="app">
    <InvoiceForm />
  </div>
</template>

<script lang="ts">
import { defineComponent } from "vue";
import InvoiceForm from "./components/InvoiceForm.vue";

export default defineComponent({
  name: "App",
  components: {
    InvoiceForm,
  },
});
</script>

<style>
body {
  font-family: Avenir, Helvetica, Arial, sans-serif;
  margin: 0;
  padding: 0;
}
#app {
  padding: 20px;
}
</style>
