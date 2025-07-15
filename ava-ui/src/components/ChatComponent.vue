<template>
  <div class="logout-section">

    <Button icon="pi pi-sign-out" label="Logout" class="logoutButton" text @click="handleLogout" />
  </div>
  <div class="chat-container">
    <div class="chat-header">
      <div class="header-content">
        <img src="@/assets/ava.png" alt="Ava Logo" class="ava-logo" />
        <span class="header-title">Women's Health Research Assistant</span>
        <div class="commands-section">
          <Button 
            icon="pi pi-cog" 
            :disabled="loading" 
            label="Inference Settings" 
            class="InferenceSettingsButton" 
            text 
            @click="showInferenceConfig = true"
            style="margin-right: 1rem;"
          />
          <input class="mr-2"
            type="file"
            :disabled="loading" 
            ref="templateFileInput"
            accept=".txt"
            style="display: none"
            @change="handleTemplateUpload"
          />
          <Button 
            icon="pi pi-upload" 
            label="Upload Template" 
            :disabled="loading" 
            class="templateButton" 
            text 
            @click="() => templateFileInput?.click()"
            style="margin-right: 1rem;"
          />
          <Select 
            v-model="modelValue" 
            :loading="modelsLoading" 
            :disabled="loading" 
            :options="models"
            optionLabel="modelName" 
            placeholder="Select Model" 
            class="model-dropdown" 
            @change="handleModelChange"
          />
        </div>
      </div>
    </div>
    <div class="messages-container">
      <ScrollPanel ref="scrollPanel" class="chat-messages custom-scrollbar">
        <div class="messages-wrapper">
          <Card v-if="showWelcomeMessage" class="welcome-message">
            <template #content>
              <div class="welcome-content">
                <i class="pi pi-comments welcome-icon"></i>
                <h2>Welcome!</h2>
                <p>Ask me anything, I'm here to help!</p>
              </div>
            </template>
          </Card>
          <div v-for="(message, index) in messages" :key="index" class="message-wrapper">
            <Card :class="['message', message.role]">
              <template #header>
                <div class="message-header">
                  <Avatar :icon="message.role === 'user' ? 'pi pi-user' : 'pi pi-android'"
                    :class="message.role === 'user' ? 'user-avatar' : 'assistant-avatar'" size="large" />
                  <span class="ml-2">{{ message.role === "user" ? "User" : "Assistant" }}</span>
                </div>
              </template>
              <template #content>
                <div :class="`${message.error ? 'message-content-error' : 'message-content'}`">
                  <template v-if="message.content">
                    {{ message.content }}
                  </template>
                  <template v-else-if="message.bedrockResponse">
                    <template v-for="(part, idx) in message.bedrockResponse.citations" :key="idx">
                      {{ part.generatedResponsePart.textResponsePart.text.trim() }}
                      <sup v-if="part && part.retrievedReferences.length > 0" 
                           class="citation-marker"
                           @click="() => showCitation(part)">
                        [{{ idx + 1 }}]
                      </sup>
                      {{ part.generatedResponsePart.textResponsePart.text.trim().endsWith('.') ? ' ' : '. ' }}
                    </template>
                  </template>
                </div>
              </template>
            </Card>
            <div class="message-timestamp" :class="{ 'timestamp-user': message.role === 'user' }">
              {{ formatTimestamp(message.timestamp) }}
            </div>
          </div>
        </div>
      </ScrollPanel>
    </div>
    <div v-if="loading" class="loading-container">
      <div class="loading-dots">
        <span></span>
        <span></span>
        <span></span>
      </div>
    </div>
    <div class="chat-input">
      <div class="kb-section">
        <Select v-model="selectedKnowledgeBase" :loading="knowledgeBasesloading" :disabled="loading" :options="knowledgeBases"
          optionLabel="name" placeholder="Select Knowledge Base" class="kb-dropdown" @change="handleKBChange" />
      </div>
      <div class="separator"></div>
      <div class="input-section">
        <span class="p-input-icon-right input-container">
          <InputText v-model="question" ref="messageInput" placeholder="Type your question..."
            @keyup.enter="sendMessage" :disabled="loading" />
        </span>
        <Button icon="pi pi-send" severity="primary" rounded @click="sendMessage"
          :disabled="loading || !question.trim()" />
      </div>
    </div>
  </div>


  <Dialog 
    :visible="showInferenceConfig" 
    @update:visible="(val) => showInferenceConfig = val" 
    modal 
    header="Inference Settings"
    style="width: 400px"
  >
    <div class="settings-container">
      <div class="setting-item">
        <label>Temperature ({{ temperature }})</label>
        <Slider v-model="temperature" :min="0" :max="1" :step="0.1" />
      </div>
      <div class="setting-item">
        <label>Top P ({{ topP }})</label>
        <Slider v-model="topP" :min="0" :max="1" :step="0.1" />
      </div>
      <div class="setting-item">
        <label>Max Tokens ({{ maxTokens }})</label>
        <Slider v-model="maxTokens" :min="0" :max="65536" :step="1" />
      </div>
    </div>
    <template #footer>
      <Button label="Save" @click="saveSettings" severity="success" />
      <Button label="Cancel" @click="showInferenceConfig = false" text />
    </template>
  </Dialog>
  <Dialog :visible="citationDialogVisible" @update:visible="(val) => citationDialogVisible = val" modal
    header="Citation Sources" style="max-width: 900px;">
    <div v-for="(item, index) in currentCitation?.retrievedReferences"
      :key="`reference-${index}-${item?.location?.s3Location?.uri}`" style="display: flex; gap: 1rem;">
      <div
        style="width: 20px; display: flex; font-weight: bold; align-items: center; padding-right: 1rem; padding-top: 1rem; padding-bottom: 1rem;">
        <Divider layout="vertical" class="!flex md:!hidden" align="center"><b>{{ index + 1 }}</b></Divider>
      </div>
      <div style="flex: 1;">
        <div class="citation-section" style="margin-bottom: 1rem;">
          <Divider align="left" type="solid">
            <b style="font-weight: bold;">Object Name</b>
          </Divider>
          <p style="margin-top: 0.75rem; padding: 0 0.5rem;">
            {{ item?.location?.s3Location?.uri }}
          </p>
        </div>
        <div class="citation-section">
          <Divider align="left" type="solid">
            <b>Text Extracted</b>
          </Divider>
          <p style="margin-top: 0.75rem; padding: 0 0.5rem;">
            {{ item.content.text }}
          </p>
        </div>
      </div>
    </div>
  </Dialog>
</template>


<script setup lang="ts">
import { ref, onMounted, computed, onUnmounted } from "vue";
import Dialog from 'primevue/dialog';
import Slider from 'primevue/slider';
import { fetchAuthSession, type AuthTokens, signOut } from "@aws-amplify/auth";
// Dialog components imported directly
import router from "../router";
import Card from "primevue/card";
import Avatar from "primevue/avatar";
import Button from "primevue/button";
import InputText from "primevue/inputtext";
import ScrollPanel from "primevue/scrollpanel";
import { APIService, type KnowledgeBaseType } from "@/services/api";
import type { BedrockKnowledgeBaseResponseType, BedrockModelResponseType, Citation } from "@/types/bedrockKnowledgeBaseResponseType";

const knowledgeBases = ref<KnowledgeBaseType[]>([]);
const selectedKnowledgeBase = ref<KnowledgeBaseType | null>(null);
const knowledgeBasesloading = ref(false);

// Model state management
const models = ref<BedrockModelResponseType[]>([]);
const selectedModel = ref<BedrockModelResponseType | null>(null);
const modelsLoading = ref(false);

// Computed property to ensure model select is properly updated
const modelValue = computed({
  get: () => selectedModel.value,
  set: (value) => {
    selectedModel.value = value;
    if (value) {
      localStorage.setItem('selectedModel', JSON.stringify(value));
    }
  }
});
const apiService = new APIService;
interface PrimeVueInputText extends InstanceType<typeof InputText> {
  $el: HTMLElement;
}


// Add this function to fetch knowledge bases and models
const fetchKnowledgeBases = async () => {
  try {
    knowledgeBasesloading.value = true;
    modelsLoading.value = true;
    if (!idToken) {
      throw new Error('No authentication tokens found');
    }
    const knowledgeBasesResponse = await apiService.getKnowledgeBasesAndModels();
    const modelsResponse = await apiService.getModels();

    // Check if response has the expected structure
    if (!knowledgeBasesResponse || !Array.isArray(knowledgeBasesResponse.knowledgeBases)) {
      console.error('Unexpected response structure:', knowledgeBasesResponse);
      throw new Error('Invalid response format from API');
    }

    // Map the response data directly without reactive wrapping
    knowledgeBases.value = knowledgeBasesResponse.knowledgeBases.map(kb => ({
      name: kb.name || 'Unnamed',
      id: kb.id || 'no-id'
    }));

    // Set the default selected KB to the first one in the list
    if (knowledgeBases.value.length > 0) {
      selectedKnowledgeBase.value = knowledgeBases.value[0];
    }
    
    // Handle models data
    if (Array.isArray(modelsResponse)) {
      models.value = modelsResponse;
      if (models.value.length > 0) {
        selectedModel.value = models.value[0];
      }
    }
  } catch (error) {
    console.error('Error fetching knowledge bases:', error);
    messages.value.push({
      role: "assistant",
      content: `Error retrieving Knowledgebases: ${error}`,
      timestamp: new Date(),
      error: true
    });

  }
  finally {
    knowledgeBasesloading.value = false;
    modelsLoading.value = false;

    setTimeout(() => {
      focusInput();
    }, 0);
  }
};
interface ChatMessage {
  role: "user" | "assistant";
  content?: string;
  bedrockResponse?: BedrockKnowledgeBaseResponseType;
  error?: boolean;
  timestamp: Date;
  chatbotRequestId?: string;
  status?: string;
}
const formatTimestamp = (timestamp: Date) => {
  return new Intl.DateTimeFormat('en-US', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: true
  }).format(timestamp);
};

const question = ref("");
const loading = ref(false);
const messages = ref<ChatMessage[]>([]);
const tokens = ref<AuthTokens>() || null;
const showWelcomeMessage = ref(true);
interface PrimeVueInputText extends InstanceType<typeof InputText> {
  $el: HTMLElement;
}

const messageInput = ref<PrimeVueInputText | null>(null);

// Settings dialog component
const showInferenceConfig = ref(false);
const temperature = ref(0);
const topP = ref(1);
const maxTokens = ref(2000);

onMounted(() => {
  // Load settings from localStorage
  const savedSettings = localStorage.getItem('modelSettings');
  if (savedSettings) {
    const settings = JSON.parse(savedSettings);
    temperature.value = settings.temperature;
    topP.value = settings.topP;
    maxTokens.value = settings.maxTokens;
  }
});

const saveSettings = () => {
  const settings = {
    temperature: temperature.value,
    topP: topP.value,
    maxTokens: maxTokens.value
  };
  localStorage.setItem('modelSettings', JSON.stringify(settings));
  modelSettings.value = settings;
  showInferenceConfig.value = false;
};

const modelSettings = ref({
  temperature: temperature.value,
  topP: topP.value,
  maxTokens: maxTokens.value,
});

const focusInput = () => {
  if (messageInput.value?.$el) {
    const inputElement = messageInput.value.$el as HTMLInputElement;
    inputElement.focus();
  } else {
    console.log("Message input ref not available");
  }
};

const idToken = computed(async () => {
  (await fetchAuthSession()).tokens?.idToken
});

const handleKBChange = () => {
  messages.value = [];
  showWelcomeMessage.value = true;
  // Save selected KB to localStorage and ensure it's set by ID
  if (selectedKnowledgeBase.value) {
    const selectedId = selectedKnowledgeBase.value.id;
    const matchingKB = knowledgeBases.value.find(kb => kb.id === selectedId);
    if (matchingKB) {
      selectedKnowledgeBase.value = matchingKB;
      localStorage.setItem('selectedKnowledgeBase', JSON.stringify({ id: matchingKB.id, name: matchingKB.name }));
    }
  }
  setTimeout(() => {
    focusInput();
  }, 10);
};

const handleModelChange = () => {
  console.log('Selected model:', selectedModel.value);
  // Save selected model to localStorage and ensure it's set by modelArn
  if (selectedModel.value) {
    const selectedArn = selectedModel.value.modelArn;
    const matchingModel = models.value.find(model => model.modelArn === selectedArn);
    if (matchingModel) {
      selectedModel.value = matchingModel;
      modelValue.value = matchingModel;
      localStorage.setItem('selectedModel', JSON.stringify({ modelArn: matchingModel.modelArn, modelName: matchingModel.modelName }));
    }
  }
};

const handleLogout = () => {
  signOut();
  router.push('/');
};
onMounted(async () => {
  try {
    // Load saved model settings from localStorage
    const savedSettings = localStorage.getItem('modelSettings');
    if (savedSettings) {
      modelSettings.value = JSON.parse(savedSettings);
    }

    // First fetch all knowledge bases and models
    await fetchKnowledgeBases();

    // Then try to set saved model from localStorage
    const savedModel = localStorage.getItem('selectedModel');
    if (savedModel && models.value.length > 0) {
      const parsedModel = JSON.parse(savedModel);
      const matchingModel = models.value.find(model => model.modelArn === parsedModel.modelArn);
      if (matchingModel) {
        selectedModel.value = matchingModel;
        modelValue.value = matchingModel;
      } else {
        // If no match found, set to first available model
        selectedModel.value = models.value[0];
        modelValue.value = models.value[0];
      }
    }

    // Try to set saved KB from localStorage
    const savedKB = localStorage.getItem('selectedKnowledgeBase');
    if (savedKB && knowledgeBases.value.length > 0) {
      const parsedKB = JSON.parse(savedKB);
      const matchingKB = knowledgeBases.value.find(kb => kb.id === parsedKB.id);
      if (matchingKB) {
        selectedKnowledgeBase.value = matchingKB;
      } else {
        // If no match found, set to first available KB
        selectedKnowledgeBase.value = knowledgeBases.value[0];
      }
    }

    if (!idToken) {
      console.error('No valid session found');
      return;
    }
    focusInput();
  } catch (error) {
    console.error('Authentication error:', error);
  }
});
const scrollPanel = ref();
const currentCitation = ref<Citation | null>(null);
const citationDialogVisible = ref(false);

const showCitation = (citation: Citation) => {
  currentCitation.value = citation;
  citationDialogVisible.value = true;
};

const scrollToBottom = () => {
  if (scrollPanel.value) {
    setTimeout(() => {
      scrollPanel.value.$el.querySelector('.p-scrollpanel-content').scrollTop =
        scrollPanel.value.$el.querySelector('.p-scrollpanel-content').scrollHeight;
    }, 100);
  }
};

const templateFileInput = ref<HTMLInputElement | null>(null);
const customTemplate = ref<string | null>(null);

const handleTemplateUpload = async (event: Event) => {
  const fileInput = event.target as HTMLInputElement;
  const file = fileInput.files?.[0];

  if (!file) return;

  if (!file.name.endsWith('.txt')) {
    messages.value.push({
      role: "assistant",
      content: "Please upload a .txt file for the template.",
      timestamp: new Date(),
      error: true
    });
    fileInput.value = '';
    return;
  }

  try {
    const text = await file.text();
    
    // Log template content when uploaded
    // console.log('=== Template Upload Debug ===');
    // console.log('Template file name:', file.name);
    // console.log('Template length:', text.length);
    // console.log('Template preview:', text.substring(0, 100));
    // console.log('=== End Template Upload Debug ===');
    
    customTemplate.value = text;
    messages.value.push({
      role: "assistant",
      content: `Template updated successfully: ${file.name}`,
      timestamp: new Date(),
      error: false
    });
  } catch (error) {
    messages.value.push({
      role: "assistant",
      content: `Error reading template file: ${error}`,
      timestamp: new Date(),
      error: true
    });
  }
  fileInput.value = '';
};

const pollStatus = async (chatbotRequestId: string) => {
  try {
    const record = await apiService.pollChatbotStatus(chatbotRequestId);
    return record;
  } catch (error) {
    console.error('Error polling status:', error);
    throw error;
  }
};

const sendMessage = async () => {
  if (!question.value.trim()) return;
  try {
    showWelcomeMessage.value = false;
    if (!selectedKnowledgeBase.value) {
      console.error('No knowledge base selected');
      messages.value.push({
        role: "assistant",
        content: "Please select a knowledge base before sending a message.",
        timestamp: new Date(),
        error: true
      });
      return;
    }

    const userMessage = question.value;
    messages.value.push({ role: "user", content: userMessage, timestamp: new Date() });
    question.value = "";
    loading.value = true;
    scrollToBottom();

    const payload = {
      message: userMessage,
      knowledgeBaseId: selectedKnowledgeBase.value.id,
      textPromptTemplate: customTemplate.value,
      textInferenceConfig: {
        maxTokens: String(modelSettings.value.maxTokens),
        stopSequences: [],
        temperature: String(modelSettings.value.temperature),
        topP: String(modelSettings.value.topP)
      },
      modelArn: selectedModel.value?.modelArn || "anthropic.claude-3-sonnet-20240229-v1:0"
    };

    const response = await apiService.submitKnowledgeBase(payload);
    const chatbotRequestId = response.chatbot_request_id;
    
    const messageIndex = messages.value.push({ 
      role: "assistant",
      content: "Processing your request...",
      timestamp: new Date(),
      chatbotRequestId: chatbotRequestId,
      status: "processing"
    }) - 1;

    // Create polling interval
    const startTime = Date.now();
    const TIMEOUT_DURATION = 120000; // 120 seconds
    let pollInterval: ReturnType<typeof setInterval>;

    // Cleanup function
    const cleanup = () => {
      if (pollInterval) {
        clearInterval(pollInterval);
      }
    };

    // Register cleanup on component unmount
    onUnmounted(cleanup);

    pollInterval = setInterval(async () => {
      try {
        // Check for timeout
        if (Date.now() - startTime > TIMEOUT_DURATION) {
          cleanup();
          messages.value[messageIndex] = {
            role: "assistant",
            content: "Request timed out after 120 seconds",
            timestamp: new Date(),
            error: true,
            chatbotRequestId: chatbotRequestId,
            status: "timeout"
          };
          loading.value = false;
          scrollToBottom();
          return;
        }

        const status = await pollStatus(chatbotRequestId);
        if (status.status === 'success') {
          cleanup();
          messages.value[messageIndex] = {
            role: "assistant",
            timestamp: new Date(),
            bedrockResponse: status.result,
            chatbotRequestId: chatbotRequestId,
            status: "success"
          };
          loading.value = false;
        } else if (status.status === 'error' || status.status === 'failed') {
          cleanup();
          messages.value[messageIndex] = {
            role: "assistant",
            content: `Error: ${status.result}`,
            timestamp: new Date(),
            error: true,
            chatbotRequestId: chatbotRequestId,
            status: "error"
          };
          loading.value = false;
        }
        scrollToBottom();
      } catch (error) {
        console.error('Polling error:', error);
        cleanup();
        messages.value[messageIndex] = {
          role: "assistant",
          content: `Error polling for response: ${error}`,
          timestamp: new Date(),
          error: true,
          chatbotRequestId: chatbotRequestId,
          status: "error"
        };
        loading.value = false;
      }
    }, 2000);

  } catch (error) {
    messages.value.push({
      role: "assistant",
      content: `${error}`,
      error: true,
      timestamp: new Date()
    });
    loading.value = false;
  } finally {
    scrollToBottom();
    setTimeout(() => {
      focusInput();
    }, 10);
  }
};

</script>

<style scoped>
.commands-section {
  display: flex;
  justify-content: flex-end;  /* Aligns content to the right */
  margin-left: auto;
}
.loading-container {
  position: fixed;
  bottom: 80px;
  /* Adjust this value based on your input section height */
  left: 0;
  right: 0;
  display: flex;
  justify-content: center;
  z-index: 100;
}

.loading-dots {
  display: flex;
  gap: 4px;
  align-items: center;
  background-color: white;
  padding: 8px 16px;
  border-radius: 16px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.loading-dots span {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background-color: #666;
  display: inline-block;
  animation: bounce 1.4s infinite ease-in-out both;
}

.loading-dots span:nth-child(1) {
  animation-delay: -0.32s;
}

.loading-dots span:nth-child(2) {
  animation-delay: -0.16s;
}

@keyframes bounce {

  0%,
  80%,
  100% {
    transform: scale(0);
  }

  40% {
    transform: scale(1);
  }
}

.citation-section {
  width: 100%;
}

:deep(.p-scrollpanel-bar) {
  background: #888 !important;
  /* Force the bar to be visible */
  opacity: 0.6 !important;
  border-radius: 4px;
}

.ava-logo {
  width: 40px;
  /* Adjust size as needed */
  height: 40px;
  /* Adjust size as needed */
  object-fit: contain;
}

.timestamp-user {
  align-self: flex-end;
  /* Align timestamp to the right for user messages */
}

.message-wrapper {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  margin-bottom: 1rem;
}

.message-wrapper .message {
  margin-bottom: 4px;
  /* Space between message and timestamp */
}

.message-timestamp {
  font-size: 0.75rem;
  color: var(--text-color-secondary);
  opacity: 0.8;
  padding: 0 0.5rem;
}

.logout-section {
  position: fixed;
  top: 1rem;
  right: 1rem;
  z-index: 1000;
}

.chat-header {
  flex: 0 0 auto;
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem;
  background-color: #e8f5e9 !important; /* Lighter green for better contrast */
  border-bottom: 1px solid gray;
  border-radius: 8px 8px 0 0;
}

.header-content {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
  width: 100%;
}

.header-icon {
  font-size: 1.5rem;
  color: var(--primary-color);
}

.header-title {
  font-size: 1.25rem;
  font-weight: 600;
  color: #2e7d32; /* Darker text for better contrast on light background */
}

.logoutButton {
  background-color: var(--p-emerald-50) !important;
  border: var(--p-emerald-200) !important;
  border-radius: 6px;
  transition: background-color 0.2s, color 0.2s, border-color 0.2s;
  box-shadow: 0 0 10px rgba(0, 0, 0, 0.295);
}

:deep(.logoutButton:hover) {
  background-color: var(--p-emerald-200) !important;
}


.welcome-message {
  max-width: 800px;
  text-align: center;
  position: absolute;
  min-width: 600px;
  top: 40%;
  left: 50%;
  transform: translate(-50%, -50%);
  margin: 2rem auto;
  background-color: white !important;
  box-shadow: 0 0 50px rgba(0, 0, 0, 0.295) !important;
  border: 2px solid var(--p-green-100);
}

.welcome-content {
  text-align: center;
  padding: 2rem;
}

.welcome-icon {
  font-size: 3rem;
  color: var(--primary-color);
  margin-bottom: 1rem;
}

.welcome-content h2 {
  color: var(--text-color);
  margin: 1rem 0;
}

.welcome-content p {
  color: var(--text-secondary-color);
  margin: 0.5rem 0;
}

.login-section {
  padding: 10px;
}

.chat-container {
  position: fixed;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  width: 95%;
  max-width: 1800px;
  height: 90vh;
  max-height: 1200px;
  background: #f5f5f5; /* Light gray background instead of transparent green */
  box-shadow: 0 0 50px rgba(0, 0, 0, 0.295);
  border-radius: 8px;
  display: flex;
  flex-direction: column;
}

.messages-container {
  flex: 1;
  min-height: 0;
  position: relative;
  display: flex;
  flex-direction: column;
}

.chat-messages {
  flex: 1;
  margin: 1rem;
  border-radius: 0.5rem;
  overflow: hidden;
}

.messages-wrapper {
  padding: 1rem;
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.message {
  max-width: 85%;
  min-width: 600px;
  background-color: var(--surface-card) !important;
}

.message.user {
  margin-left: auto;
  background-color: #e3f2fd !important; /* Light blue background */
}

.message.user :deep(.p-card-content) {
  color: #0d47a1; /* Dark blue text for good contrast */
  background-color: transparent;
}

.message.user :deep(.p-card-body) {
  padding: 10px !important;
}

.message.user :deep(.p-card-header) {
  margin: 0;
  color: #0d47a1;
  background-color: rgba(13, 71, 161, 0.1); /* Slightly tinted header */
}

.message.assistant {
  margin-right: auto;
  background-color: #f5f5f5 !important; /* Light gray background */
  color: #212121; /* Dark text for contrast */
}

.message-content {
  padding: 0.1rem;
  white-space: pre-wrap;
  color: #212121; /* Ensure text is always dark and readable */
}

.message.assistant :deep(.p-card-content) {
  color: #212121 !important; /* Force dark text color for assistant messages */
}

.message.assistant :deep(.p-card-header) {
  margin: 0;
  background-color: #e0e0e0; /* Slightly darker header background */
  color: #212121; /* Dark text for contrast */
}

.message-header {
  display: flex;
  align-items: center;
  padding: 0.1rem;
}

.message-content-error {
  color: var(--p-red-500);
  white-space: pre-wrap;
  padding: 0.1rem;
}

.citation-marker {
  cursor: pointer;
  color: var(--p-primary-500);
  margin: 0 2px;
}

.citation-marker:hover {
  text-decoration: underline;
  font-weight: bold;
}

.chat-input {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  padding: 1rem;
  background: #ffffff; /* White background for input area */
  border-radius: 0 0 1rem 1rem;
  gap: 1rem;
  border-top: 1px solid var(--surface-border);
}

.kb-section {
  flex: 0 0 auto;
}

.separator {
  width: 1px;
  height: 2rem;
  background-color: var(--p-primary-300);
  margin: 0 0.5rem;
}

.input-section {
  flex: 1;
  display: flex;
  gap: 0.5rem;
  align-items: center;
}

.input-container {
  display: flex;
  flex: 1;
}

:deep(.input-container .p-inputtext) {
  width: 100%;
}

.kb-dropdown {
  min-width: 200px;
}

.user-avatar {
  background: none !important;
}

.assistant-avatar {
  background: none !important;
}

:deep(.kb-dropdown .p-dropdown) {
  border-radius: 6px;
}

:deep(.kb-dropdown .p-dropdown:not(.p-disabled):hover) {
  border-color: var(--primary-color);
}

:deep(.kb-dropdown .p-dropdown.p-focus) {
  box-shadow: 0 0 0 1px var(--primary-color);
  border-color: var(--primary-color);
}

:deep(.p-card) {
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

:deep(.p-card-content) {
  padding: 0 !important;
}

:deep(.custom-scrollbar .p-scrollpanel-wrapper) {
  border-radius: 0.5rem;
}

:deep(.custom-scrollbar .p-scrollpanel-bar) {
  background: var(--primary-color);
  opacity: 0.5;
}

:deep(.p-scrollpanel) {
  height: 100%;
}

:deep(.p-scrollpanel-content) {
  height: 100%;
}

.welcome-container {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: calc(100vh - 200px);
}

.templateButton {
  background-color: var(--p-emerald-50) !important;
  border: var(--p-emerald-200) !important;
  border-radius: 6px;
  transition: background-color 0.2s, color 0.2s, border-color 0.2s;
  box-shadow: 0 0 10px rgba(0, 0, 0, 0.295);
}

:deep(.templateButton:hover) {
  background-color: var(--p-emerald-200) !important;
}

.InferenceSettingsButton {
  background-color: var(--p-emerald-50) !important;
  border: var(--p-emerald-200) !important;
  border-radius: 6px;
  transition: background-color 0.2s, color 0.2s, border-color 0.2s;
  box-shadow: 0 0 10px rgba(0, 0, 0, 0.295);
}

:deep(.InferenceSettingsButton:hover) {
  background-color: var(--p-emerald-200) !important;
}

.settings-container {
  padding: 1rem;
}
.setting-item {
  margin-bottom: 1.5rem;
}
.setting-item label {
  display: block;
  margin-bottom: 0.5rem;
  font-weight: 500;
}
</style>
