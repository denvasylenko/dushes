import { createApp } from 'vue'
import { createVuetify } from 'vuetify'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'
import { VDateInput } from 'vuetify/labs/VDateInput'
import 'vuetify/styles'
import App from './App.vue'

const vuetify = createVuetify({ components: { ...components, VDateInput }, directives })
createApp(App).use(vuetify).mount('#app')
