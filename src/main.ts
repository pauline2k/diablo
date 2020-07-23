import '@mdi/font/css/materialdesignicons.min.css'
import 'tiptap-vuetify/dist/main.css'
import 'vuetify/dist/vuetify.min.css'
import _ from 'lodash'
import App from './App.vue'
import axios from 'axios'
import moment from 'moment-timezone'
import router from './router'
import store from './store'
import { TiptapVuetifyPlugin } from 'tiptap-vuetify'
import Vue from 'vue'
import VueMoment from 'vue-moment'
import vuetify from './plugins/vuetify'

Vue.use(TiptapVuetifyPlugin, {
  vuetify,
  iconsGroup: 'md'
})
Vue.use(VueMoment, { moment })

const apiBaseUrl = process.env.VUE_APP_API_BASE_URL
const isDebugMode = _.trim(process.env.VUE_APP_DEBUG).toLowerCase() === 'true'

const axiosErrorHandler = error => {
  const errorStatus = _.get(error, 'response.status')
  if (_.get(Vue.prototype.$currentUser, 'isAuthenticated')) {
    if (errorStatus === 404) {
      router.push({ path: '/404' })
    } else if (errorStatus >= 400) {
      const message = _.get(error, 'response.data.message') || error.message
      console.error(message)
      router.push({
        path: '/error',
        query: {
          m: message
        }
      })
    }
  } else {
    router.push({
      path: '/login',
      query: {
        m: 'Your session has expired'
      }
    })
  }
}

// Axios
axios.defaults.withCredentials = true
axios.interceptors.response.use(
    response => response.headers['content-type'] === 'application/json' ? response.data : response,
    error => {
      const errorStatus = _.get(error, 'response.status')
      if (_.includes([401, 403], errorStatus)) {
        // Refresh user in case his/her session expired.
        return axios.get(`${apiBaseUrl}/api/user/my_profile`).then(data => {
          Vue.prototype.$currentUser = data
          axiosErrorHandler(error)
          return Promise.reject(error)
        })
      } else {
        axiosErrorHandler(error)
        return Promise.reject(error)
      }
    })

// Vue config
Vue.config.productionTip = isDebugMode
Vue.config.errorHandler = function(error, vm, info) {
  console.error(error || info)
  router.push({
    path: '/error',
    query: {
      m: _.get(error, 'message') || info
    }
  })
}

// Vue prototype
Vue.prototype.$_ = _
Vue.prototype.$loading = () => store.dispatch('context/loadingStart')
Vue.prototype.$ready = label => store.dispatch('context/loadingComplete', label)

axios.get(`${apiBaseUrl}/api/user/my_profile`).then(data => {
  Vue.prototype.$currentUser = data

  axios.get(`${apiBaseUrl}/api/config`).then(data => {
    Vue.prototype.$config = data
    Vue.prototype.$config.apiBaseUrl = apiBaseUrl
    Vue.prototype.$config.isVueAppDebugMode = isDebugMode

    new Vue({
      router,
      store,
      vuetify,
      render: h => h(App),
    }).$mount('#app')
  })
})
