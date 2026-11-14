/** Stands for `@formguide/agui-chat/vue` until the package has its Vue adapter: every stand says so on the page. */
import { ref } from 'vue'

export function useFormguide(..._args: unknown[]) {
  return { plugins: ref([]), ready: ref(false), error: ref('The Vue adapter (@formguide/agui-chat/vue) is not built yet'),
           bridge: null as unknown }
}
