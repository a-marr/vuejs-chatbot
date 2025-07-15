import type { BedrockKnowledgeBaseResponseType, BedrockModelResponseType } from '@/types/bedrockKnowledgeBaseResponseType';
import type { SubmitPayloadType } from '@/types/textInferenceConfigType';
import { fetchAuthSession } from '@aws-amplify/auth';
import type { Axios, AxiosInstance, AxiosResponse } from 'axios';
import axios from 'axios';

export interface KnowledgeBaseType {
	id: string;
	name: string;
}

export interface GetResponseType {
	knowledgeBases: KnowledgeBaseType[];
}

interface ErrorResponse {
	error: string;
}



export class APIService {
	private api!: AxiosInstance;

	constructor() {
		if (!import.meta.env.VITE_APP_API_URL) {
			throw new Error('API URL is not defined in environment variables');
		}
		this.api = axios.create({
			baseURL: import.meta.env.VITE_APP_API_URL!,
			headers: {
				'Content-Type': 'application/json'
			},
		});
	}

	async getModels(): Promise<BedrockModelResponseType[]> {
		try {
			const session = await fetchAuthSession();
			const idToken = session.tokens?.idToken?.toString();
			this.api.defaults.headers.common['Authorization'] = `Bearer ${idToken}`;
			const response: AxiosResponse = await this.api.get('/models');
			return response.data;
		} catch (error: any) {
			this.handleError(error);
			throw error;
		}
	}
	async getKnowledgeBasesAndModels(): Promise<GetResponseType> {
		try {
			const session = await fetchAuthSession();
			const idToken = session.tokens?.idToken?.toString();
			this.api.defaults.headers.common['Authorization'] = `Bearer ${idToken}`;
			const response: AxiosResponse = await this.api.get('/knowledge-bases');
			return response.data;
		} catch (error: any) {
			this.handleError(error);
			throw error;
		}
	}

	async submitKnowledgeBase(payload: SubmitPayloadType): Promise<{ chatbot_request_id: string }> {
		try {
			const session = await fetchAuthSession();
			const idToken = session.tokens?.idToken?.toString();
			this.api.defaults.headers.common['Authorization'] = `Bearer ${idToken}`;
			
			const response: AxiosResponse = await this.api.post('/chatbot', payload);
			return response.data;
		} catch (error: any) {
			this.handleError(error);
			throw error;
		}
	}

	async pollChatbotStatus(requestId: string): Promise<{ status: string; result: BedrockKnowledgeBaseResponseType }> {
		try {
			const session = await fetchAuthSession();
			const idToken = session.tokens?.idToken?.toString();
			this.api.defaults.headers.common['Authorization'] = `Bearer ${idToken}`;
			
			const response: AxiosResponse = await this.api.get(`/chatbot?url=${requestId}`);
			return response.data;
		} catch (error: any) {
			this.handleError(error);
			throw error;
		}
	}

	private handleError(error: any) {
		if (error.response) {
			console.error('Server Error:', error.response.data);
			if (error.response.data.error) {
				throw new Error(error.response.data.error);
			}
			else {
				throw new Error(JSON.stringify(error.response.data));
			}
		} else if (error.request) {
			console.error('Network Error:', error.request);
			throw new Error('Network error occurred');
		} else {
			console.error('Error:', error.message);
			throw error.message;
		}
	}
}


export default APIService;
