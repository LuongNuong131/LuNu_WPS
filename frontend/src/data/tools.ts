import type { Component } from 'vue'
import { Archive, Combine, FileImage, FileOutput, FileSpreadsheet, FileText, Files, Image, Layers2, RotateCw, Scissors, Table2, Trash2 } from '@lucide/vue'

export type ToolCategory = 'PDF' | 'Office' | 'Images'
export interface OfficeTool {
  slug: string
  name: string
  description: string
  category: ToolCategory
  input: string
  output: string
  icon: Component
  popular?: boolean
  available: boolean
  multiple?: boolean
  accept: string
  options?: Array<'degrees' | 'pages'>
  badge?: string
}

export const tools: OfficeTool[] = [
  { slug: 'pdf-to-excel', name: 'PDF to Excel', description: 'Extract tables from a PDF into editable workbooks.', category: 'PDF', input: 'PDF', output: 'XLSX', icon: Table2, popular: true, available: true, accept: '.pdf' },
  { slug: 'merge-pdf', name: 'Merge PDF', description: 'Combine multiple PDFs into one organized document.', category: 'PDF', input: 'PDF', output: 'PDF', icon: Combine, popular: true, available: true, multiple: true, accept: '.pdf' },
  { slug: 'split-pdf', name: 'Split PDF', description: 'Separate every page into individual PDFs in one ZIP file.', category: 'PDF', input: 'PDF', output: 'ZIP', icon: Scissors, available: true, accept: '.pdf' },
  { slug: 'compress-pdf', name: 'Compress PDF', description: 'Reduce document size for easier sharing and storage.', category: 'PDF', input: 'PDF', output: 'PDF', icon: Archive, popular: true, available: true, accept: '.pdf' },
  { slug: 'rotate-pdf', name: 'Rotate PDF', description: 'Rotate every page by 90, 180, or 270 degrees.', category: 'PDF', input: 'PDF', output: 'PDF', icon: RotateCw, available: true, accept: '.pdf', options: ['degrees'] },
  { slug: 'pdf-to-jpg', name: 'PDF to JPG', description: 'Render PDF pages into high-quality JPG images.', category: 'PDF', input: 'PDF', output: 'ZIP', icon: FileImage, available: true, accept: '.pdf' },
  { slug: 'extract-pages', name: 'Extract pages', description: 'Create a focused PDF from selected page ranges.', category: 'PDF', input: 'PDF', output: 'PDF', icon: Layers2, available: true, accept: '.pdf', options: ['pages'] },
  { slug: 'delete-pages', name: 'Delete pages', description: 'Remove selected pages while preserving the rest.', category: 'PDF', input: 'PDF', output: 'PDF', icon: Trash2, available: true, accept: '.pdf', options: ['pages'] },
  { slug: 'pdf-to-word', name: 'PDF to Word', description: 'Turn text-based PDFs into editable Word documents.', category: 'Office', input: 'PDF', output: 'DOCX', icon: FileText, popular: true, available: true, accept: '.pdf' },
  { slug: 'word-to-pdf', name: 'Word to PDF', description: 'Create a shareable PDF from a DOC or DOCX file.', category: 'Office', input: 'DOCX', output: 'PDF', icon: Files, available: true, accept: '.doc,.docx' },
  { slug: 'excel-to-pdf', name: 'Excel to PDF', description: 'Export spreadsheets to a print-ready PDF.', category: 'Office', input: 'XLSX', output: 'PDF', icon: FileSpreadsheet, available: true, accept: '.xls,.xlsx,.csv' },
  { slug: 'powerpoint-to-pdf', name: 'PowerPoint to PDF', description: 'Export presentation slides to a portable PDF.', category: 'Office', input: 'PPTX', output: 'PDF', icon: FileOutput, available: true, accept: '.ppt,.pptx' },
  { slug: 'jpg-to-pdf', name: 'Images to PDF', description: 'Package JPG, PNG, and WEBP images into one PDF.', category: 'Images', input: 'JPG, PNG', output: 'PDF', icon: Image, available: true, multiple: true, accept: '.jpg,.jpeg,.png,.webp' },
  { slug: 'image-convert', name: 'Convert image', description: 'Convert a JPG, PNG, or WEBP into an optimized PNG.', category: 'Images', input: 'JPG, PNG', output: 'PNG', icon: Image, available: true, accept: '.jpg,.jpeg,.png,.webp' },
]

export const categories: Array<'All' | ToolCategory> = ['All', 'PDF', 'Office', 'Images']
export const getTool = (slug: string) => tools.find((tool) => tool.slug === slug)
export const allowsMultiple = (tool?: OfficeTool) => Boolean(tool?.multiple)
export const acceptForTool = (tool?: OfficeTool) => tool?.accept || '.pdf'
