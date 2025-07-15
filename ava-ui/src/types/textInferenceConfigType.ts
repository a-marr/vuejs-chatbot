export interface TextInferenceConfigType {
    maxTokens: string;
    stopSequences: string[];
    temperature: string;
    topP: string;
}

export interface SubmitPayloadType {
    message: string;
    knowledgeBaseId: string;
    textPromptTemplate?: string | null;
    textInferenceConfig: TextInferenceConfigType;
    modelArn: string;
}