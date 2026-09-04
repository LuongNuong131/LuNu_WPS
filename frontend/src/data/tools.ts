import type { Component } from 'vue'
import {
  Archive,
  Combine,
  FileSpreadsheet,
  FileText,
  Files,
  Image,
  Layers2,
  Scissors,
  Table2,
} from '@lucide/vue'

export type ToolCategory = 'PDF' | 'Office' | 'Images'

export interface OfficeTool {
  slug: string
  name: string
  shortName: string
  description: string
  category: ToolCategory
  input: string
  output: string
  icon: Component
  popular?: boolean
  available: boolean
  badge?: string
}

export const tools: OfficeTool[] = [
  {
    slug: 'pdf-to-excel',
    name: 'PDF to Excel',
    shortName: 'PDF → Excel',
    description: 'Extract tables from a PDF into editable workbooks.',
    category: 'PDF',
    input: 'PDF',
    output: 'XLSX',
    icon: Table2,
    popular: true,
    available: true,
  },
  {
    slug: 'merge-pdf',
    name: 'Merge PDF',
    shortName: 'Merge PDFs',
    description: 'Combine multiple PDF files into one organized document.',
    category: 'PDF',
    input: 'PDF',
    output: 'PDF',
    icon: Combine,
    popular: true,
    available: true,
  },
  {
    slug: 'split-pdf',
    name: 'Split PDF',
    shortName: 'Split PDF',
    description: 'Separate every page into individual PDFs in one ZIP file.',
    category: 'PDF',
    input: 'PDF',
    output: 'ZIP',
    icon: Scissors,
    available: true,
  },
  {
    slug: 'compress-pdf',
    name: 'Compress PDF',
    shortName: 'Compress PDF',
    description: 'Reduce document size while keeping it easy to share.',
    category: 'PDF',
    input: 'PDF',
    output: 'PDF',
    icon: Archive,
    popular: true,
    available: false,
    badge: 'Soon',
  },
  {
    slug: 'pdf-to-word',
    name: 'PDF to Word',
    shortName: 'PDF → Word',
    description: 'Turn PDF content into an editable Word document.',
    category: 'Office',
    input: 'PDF',
    output: 'DOCX',
    icon: FileText,
    available: false,
    badge: 'Soon',
  },
  {
    slug: 'word-to-pdf',
    name: 'Word to PDF',
    shortName: 'Word → PDF',
    description: 'Create a shareable PDF from a DOC or DOCX file.',
    category: 'Office',
    input: 'DOCX',
    output: 'PDF',
    icon: Files,
    available: false,
    badge: 'Soon',
  },
  {
    slug: 'excel-to-pdf',
    name: 'Excel to PDF',
    shortName: 'Excel → PDF',
    description: 'Export spreadsheets to a clean, print-ready PDF.',
    category: 'Office',
    input: 'XLSX',
    output: 'PDF',
    icon: FileSpreadsheet,
    available: false,
    badge: 'Soon',
  },
  {
    slug: 'jpg-to-pdf',
    name: 'JPG to PDF',
    shortName: 'Images → PDF',
    description: 'Package one or more images into a single PDF.',
    category: 'Images',
    input: 'JPG, PNG',
    output: 'PDF',
    icon: Image,
    available: false,
    badge: 'Soon',
  },
  {
    slug: 'extract-pages',
    name: 'Extract pages',
    shortName: 'Extract pages',
    description: 'Create a focused document from selected PDF pages.',
    category: 'PDF',
    input: 'PDF',
    output: 'PDF',
    icon: Layers2,
    available: false,
    badge: 'Soon',
  },
]

export const getTool = (slug: string) => tools.find((tool) => tool.slug === slug)

export const categories: Array<'All' | ToolCategory> = ['All', 'PDF', 'Office', 'Images']

export const acceptForTool = (tool?: OfficeTool) => {
  if (!tool) return '.pdf'
  if (tool.slug === 'jpg-to-pdf') return '.jpg,.jpeg,.png,.webp'
  return '.pdf'
}

export const allowsMultiple = (tool?: OfficeTool) => tool?.slug === 'merge-pdf'

export const outputLabel = (tool?: OfficeTool) => tool?.output ?? 'FILE'
