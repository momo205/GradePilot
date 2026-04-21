import { createServerClient } from '@supabase/ssr';
import { NextResponse, type NextRequest } from 'next/server';

export async function middleware(request: NextRequest) {
  let supabaseResponse = NextResponse.next({ request });

  const supabase = createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    {
      cookies: {
        getAll: () => request.cookies.getAll(),
        setAll: (cookiesToSet) => {
          // In Next middleware, request cookies are immutable. Only set on the response.
          supabaseResponse = NextResponse.next({ request });
          cookiesToSet.forEach(({ name, value, options }) =>
            supabaseResponse.cookies.set(name, value, options)
          );
        },
      },
    }
  );

  const { data: { user } } = await supabase.auth.getUser();

  const path = request.nextUrl.pathname;

  // Remove dashboard flow entirely: /dashboard* always funnels into Study Plan (or auth).
  if (path.startsWith('/dashboard')) {
    return NextResponse.redirect(new URL(user ? '/study-plan' : '/auth', request.url));
  }

  // Protect the core workspace.
  if (!user && path.startsWith('/study-plan')) {
    return NextResponse.redirect(new URL('/auth', request.url));
  }

  // Redirect authenticated users away from /auth.
  if (user && path.startsWith('/auth')) {
    return NextResponse.redirect(new URL('/study-plan', request.url));
  }

  return supabaseResponse;
}

export const config = {
  matcher: ['/dashboard/:path*', '/study-plan/:path*', '/auth'],
};
