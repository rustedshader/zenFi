'use client'

import { createContext, useContext, useEffect, useState } from 'react'

interface AuthContextType {
  isLoggedIn: boolean
  isLoading: boolean
  login: () => void
  logout: () => void
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [isLoggedIn, setIsLoggedIn] = useState(false)
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    const checkToken = () => {
      try {
        const token = document.cookie
          .split('; ')
          .find(row => row.startsWith('jwt_token='))

        if (token) {
          setIsLoggedIn(true)
        } else {
          setIsLoggedIn(false)
        }
      } catch (error) {
        console.error('Error checking auth token:', error)
        setIsLoggedIn(false)
      } finally {
        setIsLoading(false)
      }
    }

    // Initial check
    checkToken()

    // Set up an interval to periodically check the token
    const interval = setInterval(checkToken, 1000)

    return () => clearInterval(interval)
  }, [])

  const login = () => {
    setIsLoggedIn(true)
    setIsLoading(false)
  }

  const logout = () => {
    setIsLoggedIn(false)
    document.cookie =
      'jwt_token=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;'
  }

  return (
    <AuthContext.Provider value={{ isLoggedIn, isLoading, login, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}
