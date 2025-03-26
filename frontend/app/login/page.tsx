import { LoginForm } from '@/components/login-form'

export default function LoginPage() {
  return (
    <div className="flex items-center justify-center min-h-screen">
      <div className="p-6 bg-muted rounded-lg">
        <h1 className="text-2xl mb-4">Login</h1>
        <LoginForm />
      </div>
    </div>
  )
}
