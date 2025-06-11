import { Button } from '@/components/ui/button'

export default function Settings() {
  return (
    <div className="max-w-xl mx-auto py-10">
      <h1 className="text-2xl font-bold mb-6">Settings</h1>
      <form className="space-y-6">
        <div>
          <label className="block text-sm font-medium mb-1" htmlFor="username">
            Username
          </label>
          <input
            id="username"
            type="text"
            className="w-full border rounded px-3 py-2"
            placeholder="Enter your username"
          />
        </div>
        <div>
          <label className="block text-sm font-medium mb-1" htmlFor="email">
            Email
          </label>
          <input
            id="email"
            type="email"
            className="w-full border rounded px-3 py-2"
            placeholder="Enter your email"
          />
        </div>
        <Button type="submit">Save Changes</Button>
      </form>
    </div>
  )
}
