'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { Label } from '@/components/ui/label'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger
} from '@/components/ui/dialog'

interface KnowledgeBase {
  id: string
  name: string
  description: string | null
  meta_data: any | null
  table_id: string
  is_default: boolean
  created_at: string
}

function CreateKnowledgeBaseForm({ onCreate }: { onCreate: () => void }) {
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [metaData, setMetaData] = useState('')
  const [open, setOpen] = useState(false)

  const handleCreateKnowledgeBase = async (e: React.FormEvent) => {
    e.preventDefault()
    try {
      const response = await fetch('/api/knowledge_base', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          name,
          description,
          meta_data: metaData ? JSON.parse(metaData) : null
        })
      })
      if (response.ok) {
        setName('')
        setDescription('')
        setMetaData('')
        setOpen(false)
        onCreate()
      }
    } catch (error) {
      console.error('Error creating knowledge base:', error)
    }
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button>Create New Knowledge Base</Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Create New Knowledge Base</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleCreateKnowledgeBase} className="space-y-4">
          <div>
            <Label htmlFor="name">Name</Label>
            <Input
              id="name"
              value={name}
              onChange={e => setName(e.target.value)}
              required
            />
          </div>
          <div>
            <Label htmlFor="description">Description</Label>
            <Textarea
              id="description"
              value={description}
              onChange={e => setDescription(e.target.value)}
            />
          </div>
          <div>
            <Label htmlFor="metaData">Meta Data (JSON)</Label>
            <Textarea
              id="metaData"
              value={metaData}
              onChange={e => setMetaData(e.target.value)}
              placeholder='{"key": "value"}'
            />
          </div>
          <Button type="submit">Create</Button>
        </form>
      </DialogContent>
    </Dialog>
  )
}

export default function KnowledgeBase() {
  const [knowledgeBases, setKnowledgeBases] = useState<KnowledgeBase[]>([])
  const router = useRouter()

  useEffect(() => {
    fetchKnowledgeBases()
  }, [])

  const fetchKnowledgeBases = async () => {
    try {
      const response = await fetch('/api/knowledge_base')
      const data = await response.json()
      setKnowledgeBases(data)
    } catch (error) {
      console.error('Error fetching knowledge bases:', error)
    }
  }

  return (
    <div className="container mx-auto p-4">
      <div className="flex justify-between items-center mb-4">
        <h1 className="text-2xl font-bold">Finance Knowledge Base</h1>
        <CreateKnowledgeBaseForm onCreate={fetchKnowledgeBases} />
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {knowledgeBases.map(kb => (
          <Card
            key={kb.id}
            className="cursor-pointer hover:shadow-lg transition-shadow"
            onClick={() => router.push(`/knowledge_base/${kb.id}`)}
          >
            <CardHeader>
              <CardTitle>{kb.name}</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-muted-foreground">
                {kb.description || 'No description'}
              </p>
              <p className="text-xs text-muted-foreground mt-2">
                Created: {new Date(kb.created_at).toLocaleDateString()}
              </p>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  )
}
