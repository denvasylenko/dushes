import { createApp } from 'vue'
import { createRouter, createWebHashHistory } from 'vue-router'
import App from './App.vue'
import Address from './Address.vue'
import Extras from './Extras.vue'
import Personal from './Personal.vue'

export const router = createRouter({
  history: createWebHashHistory(),
  routes: [
    { path: '/', redirect: '/personal' },
    { path: '/personal', name: 'personal', component: Personal },
    { path: '/address', name: 'address', component: Address },
    { path: '/extras', name: 'extras', component: Extras },
  ],
})

createApp(App).use(router).mount('#app')
