'use client'
import { useRouter } from 'next/navigation'
import { Button } from './ui/button'
import { useAuth } from '@/contexts/auth-context'
import Link from 'next/link'

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
      <div className="flex items-center gap-2">
        {isLoggedIn ? (
          <>
            <Button variant="ghost" onClick={() => router.push('/sessions')}>
              Sessions
            </Button>
            <Button variant="ghost" onClick={handleLogout}>
              Logout
            </Button>
          </>
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
