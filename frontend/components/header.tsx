// frontend/components/header.tsx
'use client'

import { useRouter } from 'next/navigation'
import { Button } from './ui/button'
import { useAuth } from '@/contexts/auth-context'

export default function Header() {
  const router = useRouter()
  const { isLoggedIn, logout } = useAuth()

  const handleLogout = () => {
    logout()
    router.push('/login')
  }

  return (
    <header className="p-4 flex justify-between items-center">
      <h1 className="text-xl font-bold">Morphic</h1>
      <div>
        {isLoggedIn ? (
          <Button variant="ghost" onClick={handleLogout}>
            Logout
          </Button>
        ) : (
          <>
            <Button variant="ghost" onClick={() => router.push('/login')}>
              Login
            </Button>
            <Button variant="ghost" onClick={() => router.push('/register')}>
              Register
            </Button>
          </>
        )}
      </div>
    </header>
  )
}
