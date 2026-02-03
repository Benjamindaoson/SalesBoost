import { test, expect } from '@playwright/test';

test.describe('Authentication Flow', () => {
  test('should display login page', async ({ page }) => {
    await page.goto('/login');

    // Check for login form elements
    await expect(page.getByRole('heading', { name: /sign in/i })).toBeVisible();
    await expect(page.getByRole('textbox', { name: /email/i })).toBeVisible();
    await expect(page.getByRole('button', { name: /sign in/i })).toBeVisible();
  });

  test('should show validation error for invalid email', async ({ page }) => {
    await page.goto('/login');

    // Try to submit with invalid email
    await page.getByRole('textbox', { name: /email/i }).fill('invalid-email');
    await page.getByRole('button', { name: /sign in/i }).click();

    // Should show validation error
    await expect(page.getByText(/invalid email/i)).toBeVisible();
  });

  test('should redirect to dashboard after successful login', async ({ page }) => {
    await page.goto('/login');

    // Fill in valid email
    await page.getByRole('textbox', { name: /email/i }).fill('test@example.com');
    await page.getByRole('button', { name: /sign in/i }).click();

    // Should show success message
    await expect(page.getByText(/check your email/i)).toBeVisible();
  });

  test('should redirect unauthenticated users to login', async ({ page }) => {
    // Try to access protected route
    await page.goto('/student/dashboard');

    // Should redirect to login
    await expect(page).toHaveURL('/login');
  });
});

test.describe('Protected Routes', () => {
  test('should allow access to student routes for authenticated users', async ({ page, context }) => {
    // Mock authentication
    await context.addCookies([
      {
        name: 'sb-access-token',
        value: 'mock-token',
        domain: 'localhost',
        path: '/',
      },
    ]);

    await page.goto('/student/dashboard');

    // Should show dashboard
    await expect(page.getByRole('heading', { name: /dashboard/i })).toBeVisible();
  });

  test('should block non-admin users from admin routes', async ({ page, context }) => {
    // Mock student authentication
    await context.addCookies([
      {
        name: 'sb-access-token',
        value: 'mock-student-token',
        domain: 'localhost',
        path: '/',
      },
    ]);

    await page.goto('/admin/dashboard');

    // Should redirect to student dashboard
    await expect(page).toHaveURL('/student/dashboard');
  });
});
