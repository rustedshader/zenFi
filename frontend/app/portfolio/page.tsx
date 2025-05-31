'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { useAuth } from '@/contexts/auth-context'
import { toast } from 'sonner'
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle
} from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger
} from '@/components/ui/dialog'

interface Portfolio {
  id: number
  name: string
  description: string
  gcs_document_link: string | null
}

export default function Portfolio() {
  const router = useRouter()
  const { isLoggedIn, isLoading: isAuthLoading } = useAuth()
  const [portfolios, setPortfolios] = useState<Portfolio[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [isCreateDialogOpen, setIsCreateDialogOpen] = useState(false)
  const [newPortfolioName, setNewPortfolioName] = useState('')
  const [newPortfolioDescription, setNewPortfolioDescription] = useState('')
  const [isCreating, setIsCreating] = useState(false)
  const [uploadingPortfolioId, setUploadingPortfolioId] = useState<
    number | null
  >(null)

  useEffect(() => {
    if (!isAuthLoading && !isLoggedIn) {
      router.push('/login')
    }
  }, [router, isLoggedIn, isAuthLoading])

  useEffect(() => {
    if (isLoggedIn) {
      const fetchPortfolios = async () => {
        setIsLoading(true)
        try {
          const response = await fetch('/api/portfolio')
          if (!response.ok) throw new Error('Failed to fetch portfolios')
          const data = await response.json()
          setPortfolios(data)
        } catch (error) {
          console.error(error)
          toast.error('Failed to load portfolios')
        } finally {
          setIsLoading(false)
        }
      }
      fetchPortfolios()
    }
  }, [isLoggedIn])

  const handleCreatePortfolio = async () => {
    if (!newPortfolioName.trim()) {
      toast.error('Portfolio name is required')
      return
    }
    setIsCreating(true)
    try {
      const response = await fetch('/api/portfolio/create', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: newPortfolioName,
          description: newPortfolioDescription
        })
      })
      if (!response.ok) throw new Error('Failed to create portfolio')
      const newPortfolio = await response.json()
      setPortfolios([...portfolios, newPortfolio])
      setIsCreateDialogOpen(false)
      setNewPortfolioName('')
      setNewPortfolioDescription('')
      toast.success('Portfolio created successfully')
    } catch (error) {
      console.error(error)
      toast.error('Failed to create portfolio')
    } finally {
      setIsCreating(false)
    }
  }

  const handleUpload = async (portfolioId: number, file: File) => {
    if (!file) return
    setUploadingPortfolioId(portfolioId)
    try {
      const formData = new FormData()
      formData.append('file', file)
      const response = await fetch(`/api/portfolio/${portfolioId}/upload_pdf`, {
        method: 'POST',
        body: formData
      })
      if (!response.ok) throw new Error('Failed to upload PDF')
      const updatedPortfolios = await fetch('/api/portfolio').then(res =>
        res.json()
      )
      setPortfolios(updatedPortfolios)
      toast.success('PDF uploaded successfully')
    } catch (error) {
      console.error(error)
      toast.error('Failed to upload PDF')
    } finally {
      setUploadingPortfolioId(null)
    }
  }

  const handlePortfolioClick = (portfolioId: number) => {
    router.push(`/portfolio/${portfolioId}`)
  }

  if (isAuthLoading || isLoading) {
    return (
      <div className="flex min-h-screen flex-col items-center justify-center p-24">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
        <p className="mt-4 text-lg">Loading...</p>
      </div>
    )
  }

  return (
    <div className="flex min-h-screen flex-col p-8">
      <div className="max-w-7xl mx-auto w-full space-y-8">
        <div className="flex justify-between items-center">
          <h1 className="text-3xl font-bold">Your Portfolios</h1>
          <Dialog
            open={isCreateDialogOpen}
            onOpenChange={setIsCreateDialogOpen}
          >
            <DialogTrigger asChild>
              <Button>Create New Portfolio</Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>Create New Portfolio</DialogTitle>
                <DialogDescription>
                  Enter the details for your new portfolio.
                </DialogDescription>
              </DialogHeader>
              <div className="space-y-4">
                <div>
                  <Label htmlFor="name">Name</Label>
                  <Input
                    id="name"
                    value={newPortfolioName}
                    onChange={e => setNewPortfolioName(e.target.value)}
                    placeholder="Portfolio Name"
                  />
                </div>
                <div>
                  <Label htmlFor="description">Description</Label>
                  <Input
                    id="description"
                    value={newPortfolioDescription}
                    onChange={e => setNewPortfolioDescription(e.target.value)}
                    placeholder="Portfolio Description"
                  />
                </div>
              </div>
              <DialogFooter>
                <Button
                  variant="outline"
                  onClick={() => setIsCreateDialogOpen(false)}
                >
                  Cancel
                </Button>
                <Button onClick={handleCreatePortfolio} disabled={isCreating}>
                  {isCreating ? 'Creating...' : 'Create'}
                </Button>
              </DialogFooter>
            </DialogContent>
          </Dialog>
        </div>

        {portfolios.length === 0 ? (
          <div className="text-center text-gray-500 py-12">
            You have no portfolios yet. Create one to get started!
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {portfolios.map(portfolio => (
              <Card
                key={portfolio.id}
                className="cursor-pointer hover:shadow-md transition-shadow"
                onClick={() => handlePortfolioClick(portfolio.id)}
              >
                <CardHeader>
                  <CardTitle>{portfolio.name}</CardTitle>
                  <CardDescription>{portfolio.description}</CardDescription>
                </CardHeader>
                <CardContent>
                  <p>
                    PDF:{' '}
                    {portfolio.gcs_document_link ? 'Uploaded' : 'Not uploaded'}
                  </p>
                </CardContent>
                <CardFooter>
                  <Button
                    onClick={e => {
                      e.stopPropagation() // Prevent card click
                      document.getElementById(`upload-${portfolio.id}`)?.click()
                    }}
                    disabled={uploadingPortfolioId === portfolio.id}
                  >
                    {uploadingPortfolioId === portfolio.id
                      ? 'Uploading...'
                      : 'Upload PDF'}
                  </Button>
                  <input
                    id={`upload-${portfolio.id}`}
                    type="file"
                    accept="application/pdf"
                    style={{ display: 'none' }}
                    onChange={e => {
                      const file = e.target.files?.[0]
                      if (file) handleUpload(portfolio.id, file)
                    }}
                  />
                </CardFooter>
              </Card>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
