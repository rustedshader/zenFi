import { cookies } from 'next/headers'

export async function POST(req: Request, { params }: { params: { portfolio_id: string } }) {
    try {
        const portfolio_id = await params.portfolio_id;
        const cookieStore = await cookies();
        const token = cookieStore.get('jwt_token')?.value;

        if (!token) {
            return new Response('Unauthorized', { status: 401 });
        }

        const formData = await req.formData();

        if (!formData.has('file')) {
            return new Response('No file provided', { status: 400 });
        }

        const response = await fetch(
            `${process.env.NEXT_PUBLIC_BACKEND_API_URL}/portfolio/${portfolio_id}/upload_pdf`,
            {
                method: 'POST',
                headers: {
                    Authorization: `Bearer ${token}`
                },
                body: formData
            }
        );

        if (!response.ok) {
            const errorText = await response.text();
            console.error('Backend error:', response.status, errorText);
            return new Response(errorText, { status: response.status });
        }

        return new Response(response.body);
    } catch (error) {
        console.error('API route error:', error);
        return new Response('Error processing your request', { status: 500 });
    }
}