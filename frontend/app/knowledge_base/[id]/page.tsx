'use client'

import { useState, useEffect } from 'react'
import { useParams } from 'next/navigation'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { toast } from 'sonner'

interface KnowledgeBaseInfoProps {
  id: string
  name: string
  description: string
  meta_data: string
  table_id: string
  is_default: boolean
  created_at: string
}

export default function KnowledgeBasePage() {
  const { id } = useParams<{ id: string }>()
  const [chunkSize, setChunkSize] = useState<string>('')
  const [overlap, setOverlap] = useState<string>('')
  const [file, setFile] = useState<File | null>(null)
  const [url, setUrl] = useState<string>('')
  const [isUploading, setIsUploading] = useState(false)
  const [isSettingDefault, setIsSettingDefault] = useState(false)
  const [knowledgeBaseInfo, setKnowledgeBaseInfo] =
    useState<KnowledgeBaseInfoProps>({
      id: '',
      name: '',
      description: '',
      meta_data: '',
      table_id: '',
      is_default: false,
      created_at: ''
    })

  // Fetch knowledge base info when component mounts
  useEffect(() => {
    if (id) {
      getKnowledgeBaseInfo()
    }
  }, [id])

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

  const getKnowledgeBaseInfo = async () => {
    try {
      const response = await fetch('/api/knowledge_base/info', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ knowledge_base_id: id })
      })
      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.error || 'Failed To Get Knowledge Info')
      }
      const data = await response.json()
      setKnowledgeBaseInfo(data)
    } catch (error) {
      toast(
        <div>
          <strong className="text-red-600">Error</strong>
          <div>
            {error instanceof Error
              ? error.message
              : 'Failed to fetch knowledge base info.'}
          </div>
        </div>
      )
    }
  }

  const handleSetDefault = async () => {
    setIsSettingDefault(true)
    try {
      const response = await fetch('/api/knowledge_base/set_default', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ knowledge_base_id: id })
      })

      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.error || 'Failed to set default')
      }

      const data = await response.json()
      setKnowledgeBaseInfo(prev => ({ ...prev, is_default: true }))
      toast('Success!', {
        description: 'Knowledge base set as default'
      })
    } catch (error) {
      toast(
        <div>
          <strong className="text-red-600">Error</strong>
          <div>
            {error instanceof Error ? error.message : 'Failed to set default.'}
          </div>
        </div>
      )
    } finally {
      setIsSettingDefault(false)
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
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle>Upload to Knowledge Base</CardTitle>
          <Button
            variant="outline"
            onClick={handleSetDefault}
            disabled={isSettingDefault || knowledgeBaseInfo.is_default}
          >
            {isSettingDefault
              ? 'Setting...'
              : knowledgeBaseInfo.is_default
              ? 'Default'
              : 'Set as Default'}
          </Button>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="knowledge_base_id">Knowledge Base ID</Label>
              <Input id="knowledge_base_id" value={id} disabled className="" />
            </div>
            <div className="space-y-2">
              <Label htmlFor="chunk_size">
                Chunk Size (optional) (Coming Soon)
              </Label>
              <Input
                id="chunk_size"
                type="number"
                value={chunkSize}
                onChange={e => setChunkSize(e.target.value)}
                placeholder="Enter chunk size"
                disabled
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="overlap">Overlap (optional) (Coming Soon)</Label>
              <Input
                id="overlap"
                type="number"
                value={overlap}
                onChange={e => setOverlap(e.target.value)}
                placeholder="Enter overlap"
                disabled
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
