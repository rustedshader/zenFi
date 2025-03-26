import { RegisterForm } from '@/components/register-form'

export default function RegisterPage() {
  return (
    <div className="flex items-center justify-center min-h-screen">
      <div className="p-6 bg-muted rounded-lg">
        <h1 className="text-2xl mb-4">Register</h1>
        <RegisterForm />
      </div>
    </div>
  )
}
