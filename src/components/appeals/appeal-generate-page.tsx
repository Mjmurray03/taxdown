'use client';

import { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { appealApi } from '@/lib/api';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group';
import { Label } from '@/components/ui/label';
import { useToast } from '@/components/ui/use-toast';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import {
  ArrowLeft,
  FileText,
  Download,
  CheckCircle,
  Loader2,
  Copy
} from 'lucide-react';

interface AppealGeneratePageProps {
  propertyId: string;
}

export function AppealGeneratePage({ propertyId }: AppealGeneratePageProps) {
  const router = useRouter();
  const { toast } = useToast();
  const [style, setStyle] = useState('formal');
  const [generatedAppeal, setGeneratedAppeal] = useState<any>(null);

  const generateMutation = useMutation({
    mutationFn: () => appealApi.generate(propertyId, style),
    onSuccess: (data) => {
      setGeneratedAppeal(data.data);
      toast({
        title: 'Appeal Generated',
        description: 'Your appeal letter has been created successfully.',
      });
    },
    onError: (error: any) => {
      const message = error.response?.data?.error?.message || 'Failed to generate appeal';
      toast({
        title: 'Generation Failed',
        description: message,
        variant: 'destructive',
      });
    },
  });

  const downloadPdfMutation = useMutation({
    mutationFn: () => appealApi.downloadPdf(propertyId),
    onSuccess: (blob) => {
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `appeal_${propertyId}.pdf`;
      a.click();
      window.URL.revokeObjectURL(url);
    },
    onError: () => {
      toast({
        title: 'Download Failed',
        description: 'Could not download PDF. Please try again.',
        variant: 'destructive',
      });
    },
  });

  const copyToClipboard = async (text: string) => {
    await navigator.clipboard.writeText(text);
    toast({
      title: 'Copied',
      description: 'Content copied to clipboard.',
    });
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-4">
        <Link href={`/analysis/${propertyId}`}>
          <Button variant="ghost" size="sm">
            <ArrowLeft className="mr-2 h-4 w-4" /> Back to Analysis
          </Button>
        </Link>
        <div>
          <h1 className="text-2xl font-bold">Generate Appeal Letter</h1>
          <p className="text-muted-foreground">
            Create a professional appeal letter with supporting evidence
          </p>
        </div>
      </div>

      {!generatedAppeal ? (
        <Card>
          <CardHeader>
            <CardTitle>Select Letter Style</CardTitle>
            <CardDescription>
              Choose the format that best suits your needs
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            <RadioGroup value={style} onValueChange={setStyle}>
              <div className="grid gap-4 md:grid-cols-3">
                <div className="relative">
                  <RadioGroupItem value="formal" id="formal" className="sr-only" />
                  <Label
                    htmlFor="formal"
                    className={`flex flex-col p-4 rounded-lg border-2 cursor-pointer transition-colors ${
                      style === 'formal' ? 'border-blue-600 bg-blue-50' : 'border-gray-200 hover:border-gray-300'
                    }`}
                  >
                    <span className="font-semibold">Formal</span>
                    <span className="text-sm text-muted-foreground">
                      Professional tone, suitable for official submission
                    </span>
                  </Label>
                </div>
                <div className="relative">
                  <RadioGroupItem value="detailed" id="detailed" className="sr-only" />
                  <Label
                    htmlFor="detailed"
                    className={`flex flex-col p-4 rounded-lg border-2 cursor-pointer transition-colors ${
                      style === 'detailed' ? 'border-blue-600 bg-blue-50' : 'border-gray-200 hover:border-gray-300'
                    }`}
                  >
                    <span className="font-semibold">Detailed</span>
                    <span className="text-sm text-muted-foreground">
                      Comprehensive analysis with extensive evidence
                    </span>
                  </Label>
                </div>
                <div className="relative">
                  <RadioGroupItem value="concise" id="concise" className="sr-only" />
                  <Label
                    htmlFor="concise"
                    className={`flex flex-col p-4 rounded-lg border-2 cursor-pointer transition-colors ${
                      style === 'concise' ? 'border-blue-600 bg-blue-50' : 'border-gray-200 hover:border-gray-300'
                    }`}
                  >
                    <span className="font-semibold">Concise</span>
                    <span className="text-sm text-muted-foreground">
                      Brief and to the point, key facts only
                    </span>
                  </Label>
                </div>
              </div>
            </RadioGroup>

            <Button
              size="lg"
              className="w-full"
              onClick={() => generateMutation.mutate()}
              disabled={generateMutation.isPending}
            >
              {generateMutation.isPending ? (
                <>
                  <Loader2 className="mr-2 h-5 w-5 animate-spin" />
                  Generating Appeal...
                </>
              ) : (
                <>
                  <FileText className="mr-2 h-5 w-5" />
                  Generate Appeal Letter
                </>
              )}
            </Button>
          </CardContent>
        </Card>
      ) : (
        <>
          {/* Success Banner */}
          <Card className="border-green-200 bg-green-50">
            <CardContent className="py-4">
              <div className="flex items-center gap-4">
                <CheckCircle className="h-8 w-8 text-green-600" />
                <div className="flex-1">
                  <h3 className="font-semibold text-green-800">Appeal Generated Successfully</h3>
                  <p className="text-sm text-green-700">
                    Filing deadline: {generatedAppeal.filing_deadline}
                  </p>
                </div>
                <Button
                  onClick={() => downloadPdfMutation.mutate()}
                  disabled={downloadPdfMutation.isPending}
                >
                  {downloadPdfMutation.isPending ? (
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  ) : (
                    <Download className="mr-2 h-4 w-4" />
                  )}
                  Download PDF
                </Button>
              </div>
            </CardContent>
          </Card>

          {/* Content Tabs */}
          <Card>
            <CardContent className="pt-6">
              <Tabs defaultValue="letter">
                <TabsList>
                  <TabsTrigger value="letter">Appeal Letter</TabsTrigger>
                  <TabsTrigger value="summary">Executive Summary</TabsTrigger>
                  <TabsTrigger value="evidence">Evidence</TabsTrigger>
                </TabsList>

                <TabsContent value="letter" className="mt-4">
                  <div className="relative">
                    <Button
                      variant="ghost"
                      size="sm"
                      className="absolute top-2 right-2"
                      onClick={() => copyToClipboard(generatedAppeal.letter_content)}
                    >
                      <Copy className="h-4 w-4" />
                    </Button>
                    <div className="prose max-w-none p-4 bg-gray-50 rounded-lg whitespace-pre-wrap font-mono text-sm">
                      {generatedAppeal.letter_content}
                    </div>
                  </div>
                </TabsContent>

                <TabsContent value="summary" className="mt-4">
                  <div className="prose max-w-none p-4 bg-gray-50 rounded-lg whitespace-pre-wrap">
                    {generatedAppeal.executive_summary}
                  </div>
                </TabsContent>

                <TabsContent value="evidence" className="mt-4">
                  <div className="prose max-w-none p-4 bg-gray-50 rounded-lg whitespace-pre-wrap">
                    {generatedAppeal.evidence_summary}
                  </div>
                </TabsContent>
              </Tabs>
            </CardContent>
          </Card>

          {/* Next Steps */}
          <Card>
            <CardHeader>
              <CardTitle>Next Steps</CardTitle>
            </CardHeader>
            <CardContent>
              <ol className="space-y-3">
                <li className="flex items-start gap-3">
                  <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-blue-100 text-sm font-medium text-blue-700">1</span>
                  <span>Download and review your appeal letter</span>
                </li>
                <li className="flex items-start gap-3">
                  <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-blue-100 text-sm font-medium text-blue-700">2</span>
                  <span>Gather any additional supporting documents (recent appraisals, repair estimates, etc.)</span>
                </li>
                <li className="flex items-start gap-3">
                  <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-blue-100 text-sm font-medium text-blue-700">3</span>
                  <span>Submit to the Benton County Board of Equalization before the deadline</span>
                </li>
              </ol>
            </CardContent>
          </Card>
        </>
      )}
    </div>
  );
}
