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

  // Remove dashboard flow entirely: /dashboard* always funnels into Classes (or auth).
  if (path.startsWith('/dashboard')) {
    return NextResponse.redirect(new URL(user ? '/classes' : '/auth', request.url));
  }

  // Redirect legacy workspace route.
  if (path.startsWith('/study-plan')) {
    return NextResponse.redirect(new URL(user ? '/classes' : '/auth', request.url));
  }

  // Protect the core app routes.
  if (!user && (path.startsWith('/classes') || path.startsWith('/chat'))) {
    return NextResponse.redirect(new URL('/auth', request.url));
  }

  // Redirect authenticated users away from /auth.
  if (user && path.startsWith('/auth')) {
    return NextResponse.redirect(new URL('/classes', request.url));
  }

  return supabaseResponse;
}

export const config = {
  matcher: ['/dashboard/:path*', '/study-plan/:path*', '/classes/:path*', '/chat', '/auth'],
};
