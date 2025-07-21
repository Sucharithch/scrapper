import React, { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { useToast } from '@/hooks/use-toast';
import { Loader2, Download, ExternalLink, ShoppingBag, DollarSign, FileText, Palette, Image } from 'lucide-react';
import axios from 'axios';
import { saveAs } from 'file-saver';
import * as XLSX from 'xlsx';
// @ts-ignore: ESM/TypeScript import for next-themes
import { useTheme } from "next-themes";
// @ts-ignore: ESM/TypeScript import for lucide-react
import { Moon, Sun } from "lucide-react";

interface ProductData {
  product_name: string;
  price: {
    original: string;
    discounted?: string;
  };
  description: string;
  variants: string[];
  image_urls: string[];
}

const ProductScraper: React.FC = () => {
  const [url, setUrl] = useState('');
  const [loading, setLoading] = useState(false);
  const [productData, setProductData] = useState<ProductData | null>(null);
  const { toast } = useToast();
  const { theme, setTheme } = useTheme();

  const [bulkUrls, setBulkUrls] = useState('');
  const [bulkLoading, setBulkLoading] = useState(false);

  // Add this handler for file upload
  const handleBulkFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (event) => {
      const text = event.target?.result as string;
      setBulkUrls(text || '');
    };
    reader.readAsText(file);
  };

  const validateAmazonUrl = (url: string): boolean => {
    return url.includes('amazon.') && (url.includes('/dp/') || url.includes('/gp/'));
  };

  const handleScrape = async () => {
    if (!url.trim()) {
      toast({
        title: 'URL Required',
        description: 'Please enter an Amazon product URL',
        variant: 'destructive',
      });
      return;
    }

    if (!validateAmazonUrl(url)) {
      toast({
        title: 'Invalid URL',
        description: 'Please enter a valid Amazon product URL',
        variant: 'destructive',
      });
      return;
    }

    setLoading(true);
    try {
      // Always read from env and send correct payload
      // @ts-ignore: Vite import.meta.env is available
      const API_KEY = import.meta.env.VITE_BACKEND_API_KEY;
      // @ts-ignore: Vite import.meta.env is available
      const API_BASE_URL = import.meta.env.VITE_API_BASE_URL;
      const response = await axios.post(
        `${API_BASE_URL}/scrape`,
        { url: url.trim() }, // always send { url: ... }
        {
          headers: {
            'x-api-key': API_KEY,
            'Content-Type': 'application/json',
          },
        }
      );
      setProductData(response.data.data || response.data); // handle both wrapped and direct data
      toast({
        title: 'Success!',
        description: 'Product data scraped successfully',
      });
    } catch (error: any) {
      console.error('Scraping error:', error);
      let description = 'Failed to scrape product data. Please try again.';
      if (error?.response?.status === 401) description = 'Invalid API key.';
      if (error?.response?.status === 429) description = 'Rate limit exceeded. Please wait and try again.';
      if (error?.response?.status === 400) description = error?.response?.data?.error || 'Bad request.';
      if (error?.response?.status === 422) description = 'Invalid request payload. Please check the URL.';
      toast({
        title: 'Scraping Failed',
        description,
        variant: 'destructive',
      });
    } finally {
      setLoading(false);
    }
  };

  const handleBulkScrape = async () => {
    if (!bulkUrls.trim()) {
      toast({
        title: 'URLs Required',
        description: 'Please enter one or more Amazon product URLs (one per line)',
        variant: 'destructive',
      });
      return;
    }
    setBulkLoading(true);
    try {
      // @ts-ignore: Vite import.meta.env is available
      const API_KEY = import.meta.env.VITE_BACKEND_API_KEY;
      // @ts-ignore: Vite import.meta.env is available
      const API_BASE_URL = import.meta.env.VITE_API_BASE_URL;
      const response = await axios.post(
        `${API_BASE_URL}/bulk-csv`,
        { url: bulkUrls.trim() },
        {
          headers: {
            'x-api-key': API_KEY,
            'Content-Type': 'application/json',
          },
          responseType: 'blob',
        }
      );
      saveAs(response.data, 'amazon-bulk-report.csv');
      toast({
        title: 'Bulk CSV Ready!',
        description: 'Your CSV file has been downloaded.',
      });
    } catch (error: any) {
      console.error('Bulk scraping error:', error);
      let description = 'Failed to process bulk scrape. Please try again.';
      if (error?.response?.status === 401) description = 'Invalid API key.';
      if (error?.response?.status === 429) description = 'Rate limit exceeded. Please wait and try again.';
      if (error?.response?.status === 400) description = error?.response?.data?.error || 'Bad request.';
      if (error?.response?.status === 422) description = 'Invalid request payload. Please check the URLs.';
      toast({
        title: 'Bulk Scraping Failed',
        description,
        variant: 'destructive',
      });
    } finally {
      setBulkLoading(false);
    }
  };

  const exportToCSV = () => {
    if (!productData) return;
    
    // Create CSV content manually
    const headers = ['Product Name', 'Original Price', 'Discounted Price', 'Description', 'Variants', 'Image URLs'];
    const data = [
      productData.product_name,
      productData.price.original,
      productData.price.discounted || '',
      productData.description.replace(/"/g, '""'), // Escape quotes
      productData.variants.join('; '),
      productData.image_urls.join('; ')
    ];
    
    // Format as CSV
    const csvContent = [
      headers.map(h => `"${h}"`).join(','),
      data.map(d => `"${d}"`).join(',')
    ].join('\n');
    
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    saveAs(blob, 'amazon-product.csv');
  };

  const exportToExcel = () => {
    if (!productData) return;
    
    const worksheet = XLSX.utils.json_to_sheet([{
      'Product Name': productData.product_name,
      'Original Price': productData.price.original,
      'Discounted Price': productData.price.discounted || '',
      'Description': productData.description,
      'Variants': productData.variants.join('; '),
      'Image URLs': productData.image_urls.join('; ')
    }]);
    
    const workbook = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(workbook, worksheet, 'Product Data');
    XLSX.writeFile(workbook, 'amazon-product.xlsx');
  };

  return (
    <div className="min-h-screen bg-gradient-subtle relative">
      {/* Theme Toggle */}
      <div className="absolute top-4 right-4 z-50">
        <Button
          variant="outline"
          size="icon"
          aria-label="Toggle theme"
          onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
        >
          {theme === "dark" ? <Sun className="h-5 w-5" /> : <Moon className="h-5 w-5" />}
        </Button>
      </div>
      <div className="container mx-auto px-4 py-8">
        {/* Header */}
        <div className="text-center mb-12 animate-fade-in">
          <h1 className="text-4xl md:text-5xl font-bold text-foreground mb-4">
            Amazon Product <span className="bg-gradient-primary bg-clip-text text-transparent">Scraper</span>
          </h1>
          <p className="text-xl text-muted-foreground max-w-2xl mx-auto">
            Paste any Amazon product URL and get clean, structured product data instantly
          </p>
        </div>

        {/* Input Section */}
        <Card className="max-w-2xl mx-auto mb-8 shadow-card animate-scale-in">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <ExternalLink className="h-5 w-5 text-primary" />
              Product URL
            </CardTitle>
            <CardDescription>
              Enter the Amazon product URL you want to scrape
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Input
                placeholder="https://www.amazon.in/product-name/dp/XXXXX..."
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                className="text-base"
                disabled={loading}
              />
            </div>
            <Button 
              onClick={handleScrape} 
              disabled={loading || !url.trim()}
              className="w-full h-12 text-base font-medium"
            >
              {loading ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Scraping Product...
                </>
              ) : (
                <>
                  <ShoppingBag className="mr-2 h-4 w-4" />
                  Scrape Product
                </>
              )}
            </Button>
          </CardContent>
        </Card>

        {/* Bulk CSV Section */}
        <Card className="max-w-2xl mx-auto mb-8 shadow-card animate-scale-in">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Download className="h-5 w-5 text-primary" />
              Bulk CSV Scraper
            </CardTitle>
            <CardDescription>
              Enter multiple Amazon product URLs (one per line) or upload a .txt file to download a CSV report
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <textarea
                placeholder="https://www.amazon.in/product1\nhttps://www.amazon.com/product2\n..."
                value={bulkUrls}
                onChange={e => setBulkUrls(e.target.value)}
                className="w-full min-h-[120px] p-2 border rounded text-base"
                disabled={bulkLoading}
              />
              {/* File upload input */}
              <input
                type="file"
                accept=".txt"
                onChange={handleBulkFileUpload}
                disabled={bulkLoading}
                className="block mt-2"
              />
              <span className="text-xs text-muted-foreground">
                Upload a .txt file with one URL per line.
              </span>
            </div>
            <Button
              onClick={handleBulkScrape}
              disabled={bulkLoading || !bulkUrls.trim()}
              className="w-full h-12 text-base font-medium"
            >
              {bulkLoading ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Processing Bulk CSV...
                </>
              ) : (
                <>
                  <Download className="mr-2 h-4 w-4" />
                  Download Bulk CSV
                </>
              )}
            </Button>
          </CardContent>
        </Card>

        {/* Results Section */}
        {productData && (
          <div className="space-y-6 animate-fade-in">
            {/* Export Buttons */}
            <div className="flex justify-center gap-4 mb-6">
              <Button 
                variant="outline" 
                onClick={exportToCSV}
                className="flex items-center gap-2"
              >
                <Download className="h-4 w-4" />
                Export CSV
              </Button>
              <Button 
                variant="outline" 
                onClick={exportToExcel}
                className="flex items-center gap-2"
              >
                <Download className="h-4 w-4" />
                Export Excel
              </Button>
            </div>

            <div className="grid md:grid-cols-2 gap-6">
              {/* Product Info */}
              <Card className="shadow-card">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <ShoppingBag className="h-5 w-5 text-primary" />
                    Product Information
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div>
                    <h3 className="font-semibold text-sm text-muted-foreground mb-2">Name</h3>
                    <p className="text-base font-medium text-black">{productData.product_name}</p>
                  </div>
                  
                  <div>
                    <h3 className="font-semibold text-sm text-muted-foreground mb-2 flex items-center gap-1">
                      <DollarSign className="h-4 w-4" />
                      Pricing
                    </h3>
                    <div className="space-y-1">
                      <p className="text-base text-black">
                        <span className="text-muted-foreground">Original:</span> {productData.price.original}
                      </p>
                      {productData.price.discounted && (
                        <p className="text-base text-success text-black">
                          <span className="text-muted-foreground">Discounted:</span> {productData.price.discounted}
                        </p>
                      )}
                    </div>
                  </div>

                  {productData.variants.length > 0 && (
                    <div>
                      <h3 className="font-semibold text-sm text-muted-foreground mb-2 flex items-center gap-1">
                        <Palette className="h-4 w-4" />
                        Variants
                      </h3>
                      <div className="flex flex-wrap gap-2">
                        {productData.variants.map((variant, index) => (
                          <Badge key={index} variant="secondary">{variant}</Badge>
                        ))}
                      </div>
                    </div>
                  )}
                </CardContent>
              </Card>

              {/* Description */}
              <Card className="shadow-card bg-gradient-to-br from-primary to-accent">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <FileText className="h-5 w-5 text-primary-foreground" />
                    Description
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-base leading-relaxed text-black whitespace-pre-line">
                    {productData.description}
                  </p>
                </CardContent>
              </Card>
            </div>

            {/* Images */}
            {productData.image_urls.length > 0 && (
              <Card className="shadow-card">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Image className="h-5 w-5 text-primary" />
                    Product Images
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    {productData.image_urls.slice(0, 8).map((url, index) => (
                      <div key={index} className="aspect-square rounded-lg overflow-hidden bg-accent">
                        <img
                          src={url}
                          alt={`Product image ${index + 1}`}
                          className="w-full h-full object-cover hover:scale-105 transition-transform duration-200"
                          onError={(e) => {
                            e.currentTarget.src = '/placeholder.svg';
                          }}
                        />
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default ProductScraper;