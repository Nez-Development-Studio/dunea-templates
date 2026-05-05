# Landing Page Template

## Stack

- **Frontend**: Vite 6 + React 18 + TypeScript + Tailwind CSS v3
- **Forms**: Dunea Form Service (serverless, no backend needed)

## Directory Layout

```
/home/project/
├── frontend/
│   ├── package.json              # Pre-installed deps — NEVER overwrite
│   ├── vite.config.ts            # Platform-managed — use edit_file only
│   ├── tsconfig.json             # Path alias: @/ → ./src/
│   ├── tailwind.config.js
│   ├── components.json           # shadcn config
│   ├── index.html
│   └── src/
│       ├── main.tsx              # App entry — BrowserRouter, Toaster
│       ├── App.tsx               # Renders <AppRoutes />
│       ├── routes.tsx            # All route definitions
│       ├── index.css             # Tailwind directives, CSS variables, font imports
│       ├── lib/
│       │   └── utils.ts          # cn() utility for class merging
│       ├── sections/             # Landing page sections
│       │   ├── Hero.tsx
│       │   ├── Features.tsx
│       │   ├── Testimonials.tsx
│       │   ├── Pricing.tsx
│       │   ├── CTA.tsx
│       │   └── Footer.tsx
│       └── components/
│           └── ui/               # shadcn/ui — pre-installed
│
└── BASE.md                       # This file
```

## Frontend Patterns

- **Routing**: All routes in `frontend/src/routes.tsx` using react-router-dom.
- **Path alias**: `@/` maps to `frontend/src/`.
- **State**: Zustand for client state. React Hook Form + Zod for forms.
- **Notifications**: Sonner is pre-installed AND `<Toaster />` is already mounted.
  Import `toast` from `sonner` in any file: `toast.success('Done!')`, `toast.error('Failed')`.
- **Icons**: Lucide React — `import { Icon } from 'lucide-react'`
- **Class merging**: `import { cn } from '@/lib/utils'`
- **shadcn/ui**: Pre-installed at `@/components/ui/<name>`. Import directly.

## Form Service

Landing pages submit forms to the Dunea Form Service — no backend code needed.

**Endpoint**: `POST /submit` to `import.meta.env.VITE_FORM_SERVICE_URL`

**Payload**:
```json
{
  "landingPageId": "window.location.hostname",
  "formId": "contact | newsletter | booking",
  "fields": { "email": "...", "name": "...", "message": "..." }
}
```

**Contact Form Pattern**:
```tsx
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { toast } from 'sonner';

const schema = z.object({
  name: z.string().min(1, 'Name is required'),
  email: z.string().email('Invalid email'),
  message: z.string().min(10, 'Message too short'),
});

type FormData = z.infer<typeof schema>;

const FORM_URL = import.meta.env.VITE_FORM_SERVICE_URL || 'https://forms.dunea.app';

export function ContactForm() {
  const { register, handleSubmit, reset, formState: { errors, isSubmitting } } = useForm<FormData>({
    resolver: zodResolver(schema),
  });

  const onSubmit = async (data: FormData) => {
    try {
      const res = await fetch(`${FORM_URL}/submit`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          landingPageId: window.location.hostname,
          formId: 'contact',
          fields: data,
        }),
      });
      if (res.ok) {
        toast.success('Message sent!');
        reset();
      } else {
        toast.error('Something went wrong');
      }
    } catch {
      toast.error('Network error');
    }
  };

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
      {/* Honeypot — hidden from users, catches bots */}
      <input type="text" name="_hp" className="hidden" tabIndex={-1} autoComplete="off" />

      <input {...register('name')} placeholder="Name" />
      {errors.name && <span className="text-red-500 text-sm">{errors.name.message}</span>}

      <input {...register('email')} type="email" placeholder="Email" />
      {errors.email && <span className="text-red-500 text-sm">{errors.email.message}</span>}

      <textarea {...register('message')} placeholder="Message" rows={4} />
      {errors.message && <span className="text-red-500 text-sm">{errors.message.message}</span>}

      <button type="submit" disabled={isSubmitting}>
        {isSubmitting ? 'Sending...' : 'Send Message'}
      </button>
    </form>
  );
}
```

**Newsletter Pattern**: Same structure with just `email` field and `formId: 'newsletter'`.

**Rules**:
- ALWAYS include the honeypot field (`name="_hp"`) for spam protection
- ALWAYS use `window.location.hostname` as `landingPageId`
- ALWAYS show toast feedback
- Submissions are viewable in the Dunea dashboard

## Section Architecture

Landing pages are compositions of sections, not monolithic files.

**Rules**:
- Each section file: under 150 lines
- Page component: only imports and composes sections, under 50 lines
- Sections are self-contained: own styles, own animations, own content
- Use framer-motion for scroll animations and entrance effects

**Page Example**:
```tsx
// frontend/src/pages/Home.tsx
import { Hero } from '@/sections/Hero';
import { Features } from '@/sections/Features';
import { Testimonials } from '@/sections/Testimonials';
import { Pricing } from '@/sections/Pricing';
import { CTA } from '@/sections/CTA';
import { Footer } from '@/sections/Footer';

export function Home() {
  return (
    <main>
      <Hero />
      <Features />
      <Testimonials />
      <Pricing />
      <CTA />
      <Footer />
    </main>
  );
}
```

## Critical Rules

1. **NEVER overwrite** `frontend/package.json` — use `pnpm add <pkg>` to add new ones.
2. **NEVER overwrite** `frontend/vite.config.ts` — use `edit_file` for changes.
3. **NEVER run** `npm init`, `npx create-vite`, or any scaffolding tool.
4. **NEVER create backend code** — landing pages are frontend-only.
5. **Always update** `frontend/src/routes.tsx` when adding new pages.

## Services

Start dev server with:

```bash
bash /home/project/start.sh
```

Or use the `start_server` tool. Preview appears automatically when port 5173 opens.
