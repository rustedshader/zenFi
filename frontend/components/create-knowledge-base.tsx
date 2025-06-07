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
import { Switch } from '@/components/ui/switch'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow
} from '@/components/ui/table'
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger
} from '@/components/ui/accordion'
import { Eye } from 'lucide-react'

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
  const [viewMode, setViewMode] = useState<'card' | 'table'>('card')
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

  const handleKnowledgeBaseClick = (id: string) => {
    router.push(`/knowledge_base/${id}`)
  }

  return (
    <div className="container mx-auto p-4">
      <Accordion type="single" collapsible className="mb-6">
        <AccordionItem value="item-1">
          <AccordionTrigger>
            <div className="flex gap-3">
              About Financial Knowledge Base <Eye />
            </div>
          </AccordionTrigger>
          <AccordionContent>
            The Financial Knowledge Base allows you to upload and organize your
            financial data, such as transactions, investments, and budgets. Once
            uploaded, you can query this data through our chat interface to gain
            insights, generate reports, or analyze trends. Create a new
            knowledge base to start managing your financial information
            efficiently.
          </AccordionContent>
        </AccordionItem>
      </Accordion>

      <div className="flex justify-between items-center mb-4">
        <h1 className="text-2xl font-bold">Finance Knowledge Base</h1>
        <div className="flex items-center space-x-4">
          <div className="flex items-center space-x-2">
            <Label htmlFor="view-toggle">Table View</Label>
            <Switch
              id="view-toggle"
              checked={viewMode === 'table'}
              onCheckedChange={() =>
                setViewMode(viewMode === 'card' ? 'table' : 'card')
              }
            />
          </div>
          <CreateKnowledgeBaseForm onCreate={fetchKnowledgeBases} />
        </div>
      </div>

      {knowledgeBases.length === 0 ? (
        <div className="text-center text-gray-500 py-12">
          No knowledge bases found. Create one to get started!
        </div>
      ) : viewMode === 'card' ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {knowledgeBases.map(kb => (
            <Card
              key={kb.id}
              className="cursor-pointer hover:shadow-lg transition-shadow"
              onClick={() => handleKnowledgeBaseClick(kb.id)}
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
      ) : (
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Name</TableHead>
              <TableHead>Description</TableHead>
              <TableHead>Created</TableHead>
              <TableHead>Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {knowledgeBases.map(kb => (
              <TableRow
                key={kb.id}
                className="cursor-pointer"
                onClick={() => handleKnowledgeBaseClick(kb.id)}
              >
                <TableCell>{kb.name}</TableCell>
                <TableCell>{kb.description || 'No description'}</TableCell>
                <TableCell>
                  {new Date(kb.created_at).toLocaleDateString()}
                </TableCell>
                <TableCell>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={e => {
                      e.stopPropagation()
                      handleKnowledgeBaseClick(kb.id)
                    }}
                  >
                    View
                  </Button>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      )}
    </div>
  )
}
