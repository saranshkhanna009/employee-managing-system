import { Shield, Lock, Eye, Database, Server, Network, FileText, Trash2, Download, AlertCircle, CheckCircle, User, ClipboardList, Mail } from 'lucide-react';
import { Link } from 'react-router-dom';
import { Button } from '../components/ui/Button';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/ui/Card';

export function PrivacyPage() {
  return (
    <div className="space-y-8 max-w-4xl">
      <div>
        <h1 className="text-4xl font-bold tracking-tight">Privacy Policy</h1>
        <p className="text-muted-foreground mt-2">Last updated: October 10, 2026</p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Shield className="h-5 w-5" />
            Our Privacy Commitment
          </CardTitle>
          <CardDescription>We believe privacy is a fundamental right. This policy explains how we handle your data.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-6 text-muted-foreground">
          <div className="prose prose-sm">
            <p>This Employee Tracking System is designed with privacy as a core principle. We follow the principle of data minimization — we only collect what is strictly necessary for the system to function, and we protect that data with strong encryption and access controls.</p>
            <p>This policy applies to all users of the system: employees, managers, administrators, and company owners.</p>
          </div>
        </CardContent>
      </Card>

      <div className="space-y-6">
        {/* Data Collection */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Database className="h-5 w-5" />
              Data We Collect
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4 text-sm text-muted-foreground">
            <div className="grid gap-4 md:grid-cols-2">
              <div className="p-4 border rounded-lg">
                <h4 className="font-medium mb-2 flex items-center gap-2">
                  <User className="h-4 w-4" />
                  Account Information
                </h4>
                <ul className="list-disc list-inside space-y-1">
                  <li>Full name (encrypted)</li>
                  <li>Email address (encrypted)</li>
                  <li>Phone number (encrypted, optional)</li>
                  <li>Employee ID (admin ID, not encrypted)</li>
                  <li>Role and department assignment</li>
                </ul>
              </div>
              <div className="p-4 border rounded-lg">
                <h4 className="font-medium mb-2 flex items-center gap-2">
                  <Lock className="h-4 w-4" />
                  Authentication Data
                </h4>
                <ul className="list-disc list-inside space-y-1">
                  <li>Password hash (Argon2id, never stored in plaintext)</li>
                  <li>Session tokens (hashed with SHA-256)</li>
                  <li>Device fingerprint (hashed user agent)</li>
                  <li>IP address at login</li>
                  <li>Login timestamps</li>
                </ul>
              </div>
              <div className="p-4 border rounded-lg">
                <h4 className="font-medium mb-2 flex items-center gap-2">
                  <ClipboardList className="h-4 w-4" />
                  Work Data
                </h4>
                <ul className="list-disc list-inside space-y-1">
                  <li>Task assignments and progress</li>
                  <li>Daily work logs (hours, notes - encrypted)</li>
                  <li>Leave requests and reasons (encrypted)</li>
                  <li>Task comments and updates</li>
                </ul>
              </div>
              <div className="p-4 border rounded-lg">
                <h4 className="font-medium mb-2 flex items-center gap-2">
                  <FileText className="h-4 w-4" />
                  Audit & Security Logs
                </h4>
                <ul className="list-disc list-inside space-y-1">
                  <li>Action type and timestamp</li>
                  <li>Resource accessed/modified</li>
                  <li>IP address and user agent</li>
                  <li>Success/failure status</li>
                  <li>Metadata (non-PII)</li>
                </ul>
              </div>
            </div>
            <p className="text-xs text-muted-foreground">
              <strong>Note:</strong> All personally identifiable information (PII) is encrypted at rest using AES-256-GCM with per-field keys derived from a master key via HKDF.
            </p>
          </CardContent>
        </Card>

        {/* Data Usage */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Eye className="h-5 w-5" />
              How We Use Your Data
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4 text-sm text-muted-foreground">
            <ul className="list-disc list-inside space-y-3">
              <li>
                <strong>Authentication & Authorization:</strong> To verify your identity and enforce role-based access control.
              </li>
              <li>
                <strong>Task Management:</strong> To assign, track, and manage work tasks within your department.
              </li>
              <li>
                <strong>Leave Management:</strong> To process leave requests, approvals, and balance tracking.
              </li>
              <li>
                <strong>Daily Tracking:</strong> To record and report on daily work progress.
              </li>
              <li>
                <strong>Security & Auditing:</strong> To detect unauthorized access, investigate incidents, and maintain compliance.
              </li>
              <li>
                <strong>Administrative Functions:</strong> For company admins to manage employees, departments, and settings.
              </li>
            </ul>
            <p className="text-xs">
              <strong>We do NOT:</strong> Sell your data, use it for advertising, share it with third parties for marketing, or use it for automated decision-making that significantly affects you.
            </p>
          </CardContent>
        </Card>

        {/* Data Storage & Security */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Lock className="h-5 w-5" />
              Data Storage & Security
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4 text-sm text-muted-foreground">
            <div className="grid gap-4 md:grid-cols-3">
              <div className="p-4 border rounded-lg text-center">
                <Lock className="h-8 w-8 mx-auto text-primary mb-2" />
                <h4 className="font-medium mb-1">Encryption at Rest</h4>
                <p>AES-256-GCM for all PII fields. Per-field keys via HKDF. Master key never stored in database.</p>
              </div>
              <div className="p-4 border rounded-lg text-center">
                <Server className="h-8 w-8 mx-auto text-primary mb-2" />
                <h4 className="font-medium mb-1">Encryption in Transit</h4>
                <p>TLS 1.3 for all connections. HSTS enforced. Certificate pinning recommended for production.</p>
              </div>
              <div className="p-4 border rounded-lg text-center">
                <Database className="h-8 w-8 mx-auto text-primary mb-2" />
                <h4 className="font-medium mb-1">Database Security</h4>
                <p>PostgreSQL with Row Level Security. No cross-company queries possible. Parameterized queries only.</p>
              </div>
            </div>
            <div className="grid gap-4 md:grid-cols-3">
              <div className="p-4 border rounded-lg text-center">
                <Network className="h-8 w-8 mx-auto text-primary mb-2" />
                <h4 className="font-medium mb-1">Session Security</h4>
                <p>HttpOnly, Secure, SameSite=Strict cookies. SHA-256 hashed tokens. Concurrent session limits. Automatic expiry.</p>
              </div>
              <div className="p-4 border rounded-lg text-center">
                <Shield className="h-8 w-8 mx-auto text-primary mb-2" />
                <h4 className="font-medium mb-1">Access Control</h4>
                <p>Role-based (RBAC) with hierarchical permissions. Company isolation enforced at database level.</p>
              </div>
              <div className="p-4 border rounded-lg text-center">
                <AlertCircle className="h-8 w-8 mx-auto text-primary mb-2" />
                <h4 className="font-medium mb-1">Audit Trail</h4>
                <p>Immutable, append-only logs with hash chaining. Tamper-evident. Admin-only access.</p>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Cookies */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Server className="h-5 w-5" />
              Cookie Policy
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4 text-sm text-muted-foreground">
            <table className="w-full text-left">
              <thead>
                <tr className="border-b">
                  <th className="pb-2 font-medium">Cookie Name</th>
                  <th className="pb-2 font-medium">Purpose</th>
                  <th className="pb-2 font-medium">Type</th>
                  <th className="pb-2 font-medium">Expiry</th>
                </tr>
              </thead>
              <tbody>
                <tr className="border-b">
                  <td className="py-2 font-mono text-sm">__Host-session</td>
                  <td>Session authentication token</td>
                  <td>Essential</td>
                  <td>24 hours (30 days with "Remember me")</td>
                </tr>
              </tbody>
            </table>
            <div className="space-y-2">
              <h4 className="font-medium">Cookie Attributes:</h4>
              <ul className="list-disc list-inside space-y-1 ml-4">
                <li><strong>HttpOnly:</strong> Yes — inaccessible to JavaScript</li>
                <li><strong>Secure:</strong> Yes — only transmitted over HTTPS</li>
                <li><strong>SameSite:</strong> Strict — not sent with cross-site requests</li>
                <li><strong>Path:</strong> / — available on all paths</li>
                <li><strong>Domain:</strong> Set to your domain (or omitted for current host)</li>
                <li><strong>Prefix:</strong> __Host- — requires Secure, Path=/, no Domain</li>
              </ul>
              <p className="text-xs">
                No analytics cookies, no advertising cookies, no third-party cookies, no tracking pixels, no fingerprinting scripts.
              </p>
            </div>
          </CardContent>
        </Card>

        {/* Data Retention */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <FileText className="h-5 w-5" />
              Data Retention
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4 text-sm text-muted-foreground">
            <table className="w-full text-left">
              <thead>
                <tr className="border-b">
                  <th className="pb-2 font-medium">Data Type</th>
                  <th className="pb-2 font-medium">Retention Period</th>
                  <th className="pb-2 font-medium">Deletion Trigger</th>
                </tr>
              </thead>
              <tbody>
                <tr className="border-b"><td className="py-2">Account data</td><td className="py-2">Active + 30 days</td><td className="py-2">Account deletion request</td></tr>
                <tr className="border-b"><td className="py-2">Task data</td><td className="py-2">Active + 2 years</td><td className="py-2">Task completion + 2 years</td></tr>
                <tr className="border-b"><td className="py-2">Daily logs</td><td className="py-2">2 years</td><td className="py-2">Automatic after 2 years</td></tr>
                <tr className="border-b"><td className="py-2">Leave requests</td><td className="py-2">3 years</td><td className="py-2">Legal requirement</td></tr>
                <tr className="border-b"><td className="py-2">Audit logs</td><td className="py-2">7 years</td><td className="py-2">Compliance requirement</td></tr>
                <tr className="border-b"><td className="py-2">Session logs</td><td className="py-2">90 days</td><td className="py-2">Automatic after 90 days</td></tr>
                <tr><td className="py-2">Password reset tokens</td><td className="py-2">1 hour</td><td className="py-2">Automatic expiry</td></tr>
              </tbody>
            </table>
          </CardContent>
        </Card>

        {/* Your Rights */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Download className="h-5 w-5" />
              Your Rights
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4 text-sm text-muted-foreground">
            <div className="grid gap-4 md:grid-cols-2">
              <div className="p-4 border rounded-lg">
                <h4 className="font-medium mb-2 flex items-center gap-2 text-green-600">
                  <CheckCircle className="h-4 w-4" />
                  Right to Access
                </h4>
                <p>Request a copy of all your personal data in machine-readable format (JSON). Available in Settings → Privacy → Export My Data.</p>
              </div>
              <div className="p-4 border rounded-lg">
                <h4 className="font-medium mb-2 flex items-center gap-2 text-green-600">
                  <CheckCircle className="h-4 w-4" />
                  Right to Rectification
                </h4>
                <p>Update your profile information (name, phone) at any time in Settings → Profile.</p>
              </div>
              <div className="p-4 border rounded-lg">
                <h4 className="font-medium mb-2 flex items-center gap-2 text-red-600">
                  <Trash2 className="h-4 w-4" />
                  Right to Erasure
                </h4>
                <p>Request deletion of your account and all personal data in Settings → Security → Delete Account. Some data may be retained for legal compliance (audit logs).</p>
              </div>
              <div className="p-4 border rounded-lg">
                <h4 className="font-medium mb-2 flex items-center gap-2 text-green-600">
                  <CheckCircle className="h-4 w-4" />
                  Right to Restrict Processing
                </h4>
                <p>Contact your company administrator to restrict processing of specific data categories.</p>
              </div>
              <div className="p-4 border rounded-lg">
                <h4 className="font-medium mb-2 flex items-center gap-2 text-green-600">
                  <CheckCircle className="h-4 w-4" />
                  Right to Data Portability
                </h4>
                <p>Export your data in JSON format for transfer to another system.</p>
              </div>
              <div className="p-4 border rounded-lg">
                <h4 className="font-medium mb-2 flex items-center gap-2 text-green-600">
                  <CheckCircle className="h-4 w-4" />
                  Right to Object
                </h4>
                <p>Object to processing for direct marketing (not applicable — we don't do marketing).</p>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Third Parties */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Network className="h-5 w-5" />
              Third-Party Sharing
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4 text-sm text-muted-foreground">
            <div className="prose prose-sm">
              <p><strong>We do not share your data with third parties</strong> except in the following limited circumstances:</p>
              <ul className="list-disc list-inside space-y-2">
                <li><strong>Within your company:</strong> Your data is visible to your managers and administrators based on role-based permissions.</li>
                <li><strong>Legal obligations:</strong> If required by law, court order, or government request.</li>
                <li><strong>Security incidents:</strong> To investigate and prevent fraud, unauthorized access, or other illegal activities.</li>
              </ul>
              <p>We do not use third-party analytics (no Google Analytics, Mixpanel, etc.), advertising networks, social media trackers, or any external services that would receive your data.</p>
            </div>
          </CardContent>
        </Card>

        {/* Self-Hosted Deployment */}
        <Card className="border-primary/50 bg-primary/5">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Server className="h-5 w-5" />
              Self-Hosted Deployment
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4 text-sm text-muted-foreground">
            <div className="prose prose-sm">
              <p>This application is designed for <strong>self-hosted deployment</strong>. When you deploy it on your own infrastructure:</p>
              <ul className="list-disc list-inside space-y-2">
                <li>You have full control over the database and all data</li>
                <li>No data leaves your network unless you configure it to</li>
                <li>You manage encryption keys, SSL certificates, and access controls</li>
                <li>You are responsible for compliance with local regulations (GDPR, CCPA, etc.)</li>
                <li>No telemetry, no phone-home, no license validation</li>
              </ul>
              <p>This privacy policy describes the default configuration. Your deployment may have additional controls or integrations.</p>
            </div>
          </CardContent>
        </Card>

        {/* Contact */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Mail className="h-5 w-5" />
              Contact
            </CardTitle>
          </CardHeader>
          <CardContent className="text-sm text-muted-foreground">
            <p>For privacy-related questions or to exercise your rights, contact your company administrator or the system administrator of your deployment.</p>
            <p className="mt-2">If you are the system administrator, you have full access to the database and can handle data subject requests directly.</p>
          </CardContent>
        </Card>
      </div>

      <div className="pt-8 border-t">
        <Button variant="outline" asChild>
          <Link to="/settings">← Back to Settings</Link>
        </Button>
      </div>
    </div>
  );
}
