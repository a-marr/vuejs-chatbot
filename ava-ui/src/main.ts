import './assets/main.css'

import { createApp } from 'vue'
import InputText from 'primevue/inputtext';
import Button from 'primevue/button';
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'
import PrimeVue from 'primevue/config';
import Aura from '@primevue/themes/aura'
import StyleClass from 'primevue/styleclass';
import 'primeicons/primeicons.css'
import { Amplify } from 'aws-amplify';

const app = createApp(App);
app.directive('styleclass', StyleClass);

Amplify.configure({
	Auth: {
		Cognito: {
			userPoolId: import.meta.env.VITE_COGNITO_USER_POOL_ID!,
			userPoolClientId: import.meta.env.VITE_COGNITO_CLIENT_ID!,
			identityPoolId: import.meta.env.VITE_COGNITO_IDENTITY_POOL_ID!,
			loginWith: {
				email: true,
			},
		},
	},
})

app.use(PrimeVue, {
	inputVariant: "filled",
	ripple: true,
	theme: {

		preset: Aura,
		options: {
			prefix: 'p',
			darkModeSelector: '.disable-dark',
			cssLayer: {
				name: 'primevue',
				order: 'tailwind-base, primevue, tailwind-utilities'
			}
		}
	}
});
app.component('InputText', InputText);
app.component('Button', Button);

app.use(createPinia())
app.use(router)

app.mount('#app')
