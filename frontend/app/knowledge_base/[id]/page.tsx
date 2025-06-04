'use client'

import { useState } from 'react'
import { useParams } from 'next/navigation'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { toast } from 'sonner'

export default function KnowledgeBasePage() {
  const { id } = useParams<{ id: string }>()
  const [chunkSize, setChunkSize] = useState<string>('')
  const [overlap, setOverlap] = useState<string>('')
  const [file, setFile] = useState<File | null>(null)
  const [url, setUrl] = useState<string>('')
  const [isUploading, setIsUploading] = useState(false)

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = e.target.files?.[0]
    if (selectedFile && selectedFile.type === 'application/pdf') {
      setFile(selectedFile)
      setUrl('') // Clear URL when file is selected
    } else {
      toast(
        <div>
          <strong className="text-red-600">Invalid file</strong>
          <div>Please select a PDF file.</div>
        </div>
      )
      setFile(null)
    }
  }

  const handleUrlChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const inputUrl = e.target.value
    setUrl(inputUrl)
    if (inputUrl) {
      setFile(null) // Clear file when URL is entered
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!file && !url) {
      toast(
        <div>
          <strong className="text-red-600">No input provided</strong>
          <div>Please select a PDF file or provide a URL.</div>
        </div>
      )
      return
    }

    setIsUploading(true)
    const formData = new FormData()
    formData.append('knowledge_base_id', id)
    if (chunkSize) formData.append('chunk_size', chunkSize)
    if (overlap) formData.append('overlap', overlap)
    if (file) formData.append('file', file)
    if (url) formData.append('url', url)

    try {
      const response = await fetch('/api/knowledge_base/upload', {
        method: 'POST',
        body: formData
      })

      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.error || 'Upload failed')
      }

      const data = await response.json()
      toast('Upload successful!', {
        description: data.message
      })
      // Reset form
      setChunkSize('')
      setOverlap('')
      setFile(null)
      setUrl('')
      // Reset file input
      const fileInput = document.getElementById('file') as HTMLInputElement
      if (fileInput) fileInput.value = ''
    } catch (error) {
      toast(
        <div>
          <strong className="text-red-600">Error</strong>
          <div>
            {error instanceof Error ? error.message : 'Failed to upload.'}
          </div>
        </div>
      )
    } finally {
      setIsUploading(false)
    }
  }

  return (
    <div className="container mx-auto py-8">
      <Card className="max-w-lg mx-auto">
        <CardHeader>
          <CardTitle>Upload to Knowledge Base</CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="knowledge_base_id">Knowledge Base ID</Label>
              <Input
                id="knowledge_base_id"
                value={id}
                disabled
                className="bg-gray-100"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="chunk_size">Chunk Size (optional)</Label>
              <Input
                id="chunk_size"
                type="number"
                value={chunkSize}
                onChange={e => setChunkSize(e.target.value)}
                placeholder="Enter chunk size"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="overlap">Overlap (optional)</Label>
              <Input
                id="overlap"
                type="number"
                value={overlap}
                onChange={e => setOverlap(e.target.value)}
                placeholder="Enter overlap"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="file">PDF File</Label>
              <Input
                id="file"
                type="file"
                accept="application/pdf"
                onChange={handleFileChange}
                disabled={!!url}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="url">URL</Label>
              <Input
                id="url"
                type="url"
                value={url}
                onChange={handleUrlChange}
                placeholder="Enter URL (e.g., https://example.com)"
                disabled={!!file}
              />
            </div>
            <Button type="submit" disabled={isUploading || (!file && !url)}>
              {isUploading ? 'Uploading...' : 'Upload'}
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  )
}
