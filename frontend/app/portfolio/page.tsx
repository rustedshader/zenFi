'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { useAuth } from '@/contexts/auth-context'
import { toast } from 'sonner'
import {
  Card,
  CardDescription,
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

interface Portfolio {
  id: string
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
    string | null
  >(null)
  const [viewMode, setViewMode] = useState<'card' | 'table'>('card')

  useEffect(() => {
    if (!isAuthLoading && !isLoggedIn) {
      router.push('/login')
    }
  }, [router, isLoggedIn, isAuthLoading])

  const fetchPortfolios = async () => {
    setIsLoading(true)
    try {
      const response = await fetch('/api/portfolio')
      if (!response.ok) throw new Error('Failed to fetch portfolios')
      const data = await response.json()
      console.log('Fetched Portfolios:', data)
      setPortfolios(data)
    } catch (error) {
      console.error(error)
      toast.error('Failed to load portfolios')
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    if (isLoggedIn) {
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
      const result = await response.json()
      console.log('API Response:', result)

      const newPortfolio: Portfolio = {
        id: result.portfolio_id,
        name: newPortfolioName,
        description: newPortfolioDescription,
        gcs_document_link: null
      }

      setPortfolios([...portfolios, newPortfolio])
      setIsCreateDialogOpen(false)
      setNewPortfolioName('')
      setNewPortfolioDescription('')
      toast.success('Portfolio created successfully')
      await fetchPortfolios()
    } catch (error) {
      console.error(error)
      toast.error('Failed to create portfolio')
    } finally {
      setIsCreating(false)
    }
  }

  const handlePortfolioClick = (portfolioId: string) => {
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
        <Accordion type="single" collapsible className="mb-6">
          <AccordionItem value="item-1">
            <AccordionTrigger>About Portfolios</AccordionTrigger>
            <AccordionContent>
              Portfolios allow you to organize and manage your financial data,
              such as assets, investments, and documents. Create a portfolio to
              group related financial information, upload relevant documents,
              and track your financial activities. You can access and analyze
              your portfolio data through our platform's features.
            </AccordionContent>
          </AccordionItem>
        </Accordion>

        <div className="flex justify-between items-center">
          <h1 className="text-3xl font-bold">Your Portfolios</h1>
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
        </div>

        {portfolios.length === 0 ? (
          <div className="text-center text-gray-500 py-12">
            You have no portfolios yet. Create one to get started!
          </div>
        ) : viewMode === 'card' ? (
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
              </Card>
            ))}
          </div>
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Name</TableHead>
                <TableHead>Description</TableHead>
                <TableHead>Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {portfolios.map(portfolio => (
                <TableRow
                  key={portfolio.id}
                  className="cursor-pointer"
                  onClick={() => handlePortfolioClick(portfolio.id)}
                >
                  <TableCell>{portfolio.name}</TableCell>
                  <TableCell>{portfolio.description}</TableCell>
                  <TableCell>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={e => {
                        e.stopPropagation()
                        handlePortfolioClick(portfolio.id)
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
    </div>
  )
}
