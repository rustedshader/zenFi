// frontend/components/login-form.tsx
'use client'

import { useAuth } from '@/contexts/auth-context'
import { useRouter } from 'next/navigation'
import { useState } from 'react'
import { toast } from 'sonner'
import { Button } from './ui/button'
import { Input } from './ui/input'

export function LoginForm() {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const router = useRouter()
  const { login } = useAuth()

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    try {
      const response = await fetch('/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password })
      })

      if (response.ok) {
        login() // Update auth state
        toast.success('Logged in successfully')

        // Use a combination of approaches for more reliable redirection
        try {
          // First try the router
          router.push('/')

          // As a fallback, also set a timeout to use window.location
          setTimeout(() => {
            if (window.location.pathname === '/login') {
              window.location.href = '/'
            }
          }, 500)
        } catch (navError) {
          console.error('Navigation error:', navError)
          // Fallback to window.location
          window.location.href = '/'
        }
      } else {
        const { error } = await response.json()
        toast.error(error || 'Login failed')
      }
    } catch (error) {
      console.error('Login error:', error)
      toast.error('Login failed - please try again')
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <Input
        type="text"
        placeholder="Username"
        value={username}
        onChange={e => setUsername(e.target.value)}
      />
      <Input
        type="password"
        placeholder="Password"
        value={password}
        onChange={e => setPassword(e.target.value)}
      />
      <Button type="submit">Login</Button>
    </form>
  )
}
