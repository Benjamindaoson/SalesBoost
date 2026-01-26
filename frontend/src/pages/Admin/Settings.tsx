import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

export default function AdminSettings() {
  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold tracking-tight">Settings</h1>

      <Card>
        <CardHeader>
          <CardTitle>General Settings</CardTitle>
          <CardDescription>Manage your platform configuration.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid w-full max-w-sm items-center gap-1.5">
            <Label htmlFor="platform-name">Platform Name</Label>
            <Input type="text" id="platform-name" placeholder="SalesBoost" defaultValue="SalesBoost" />
          </div>
          <div className="grid w-full max-w-sm items-center gap-1.5">
            <Label htmlFor="support-email">Support Email</Label>
            <Input type="email" id="support-email" placeholder="support@example.com" />
          </div>
          <Button>Save Changes</Button>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Integrations</CardTitle>
          <CardDescription>Connect with third-party services.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
           <div className="flex items-center justify-between p-4 border rounded-lg">
             <div>
               <h4 className="font-medium">OpenAI API</h4>
               <p className="text-sm text-muted-foreground">Used for AI Coach and Chat.</p>
             </div>
             <Button variant="outline">Configure</Button>
           </div>
           <div className="flex items-center justify-between p-4 border rounded-lg">
             <div>
               <h4 className="font-medium">CRM Integration</h4>
               <p className="text-sm text-muted-foreground">Sync user data with Salesforce/HubSpot.</p>
             </div>
             <Button variant="outline">Connect</Button>
           </div>
        </CardContent>
      </Card>
    </div>
  );
}
