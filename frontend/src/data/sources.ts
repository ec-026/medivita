import type { MedicalSource } from '../types'

export const TRUSTED_SOURCES: MedicalSource[] = [
  { id: 'healthline', name: 'Healthline', domain: 'healthline.com', description: 'Consumer-focused health information covering conditions, wellness and medications.' },
  { id: 'cleveland-clinic', name: 'Cleveland Clinic', domain: 'clevelandclinic.org', description: 'Patient-focused health information from Cleveland Clinic.' },
  { id: 'mayo-clinic', name: 'Mayo Clinic', domain: 'mayoclinic.org', description: 'Medical information covering diseases, symptoms, tests and treatments.' },
  { id: 'webmd', name: 'WebMD', domain: 'webmd.com', description: 'Consumer health information, medical references and wellness content.' },
]

export const SUGGESTIONS = [
  { title: 'Common migraine triggers', prompt: 'What are common migraine triggers?', icon: 'activity' },
  { title: 'Vitamin D basics', prompt: 'What should I know about vitamin D?', icon: 'pill' },
  { title: 'Understanding insulin resistance', prompt: 'What does insulin resistance mean?', icon: 'book' },
  { title: 'How sleep affects headaches', prompt: 'How can sleep patterns affect headaches?', icon: 'heart' },
] as const
