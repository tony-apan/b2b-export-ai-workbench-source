#!/usr/bin/env node

function parseArgs(argv) {
  const args = {};
  for (let index = 0; index < argv.length; index += 1) {
    const value = argv[index];
    if (value === '--url') args.url = argv[++index];
    else if (value === '--expected-content-type') args.expectedContentType = argv[++index];
    else if (value === '--help' || value === '-h') args.help = true;
    else throw new Error(`Unknown argument: ${value}`);
  }
  return args;
}

function u24le(buffer, offset) {
  return buffer[offset] | (buffer[offset + 1] << 8) | (buffer[offset + 2] << 16);
}

function parseImage(buffer) {
  if (buffer.length >= 24 && buffer.subarray(1, 4).toString('ascii') === 'PNG') {
    return { format: 'png', width: buffer.readUInt32BE(16), height: buffer.readUInt32BE(20) };
  }
  if (buffer.length >= 10 && ['GIF87a', 'GIF89a'].includes(buffer.subarray(0, 6).toString('ascii'))) {
    return { format: 'gif', width: buffer.readUInt16LE(6), height: buffer.readUInt16LE(8) };
  }
  if (buffer.length >= 16 && buffer.subarray(0, 4).toString('ascii') === 'RIFF'
      && buffer.subarray(8, 12).toString('ascii') === 'WEBP') {
    const chunk = buffer.subarray(12, 16).toString('ascii');
    if (chunk === 'VP8X' && buffer.length >= 30) {
      return { format: 'webp', width: 1 + u24le(buffer, 24), height: 1 + u24le(buffer, 27) };
    }
    if (chunk === 'VP8L' && buffer.length >= 25 && buffer[20] === 0x2f) {
      const bits = buffer.readUInt32LE(21);
      return {
        format: 'webp',
        width: (bits & 0x3fff) + 1,
        height: ((bits >> 14) & 0x3fff) + 1,
      };
    }
    const marker = buffer.indexOf(Buffer.from([0x9d, 0x01, 0x2a]), 20);
    if (marker >= 0 && marker + 7 <= buffer.length) {
      return {
        format: 'webp',
        width: buffer.readUInt16LE(marker + 3) & 0x3fff,
        height: buffer.readUInt16LE(marker + 5) & 0x3fff,
      };
    }
    return { format: 'webp', width: null, height: null };
  }
  if (buffer.length >= 4 && buffer[0] === 0xff && buffer[1] === 0xd8) {
    let offset = 2;
    while (offset + 9 < buffer.length) {
      if (buffer[offset] !== 0xff) { offset += 1; continue; }
      const marker = buffer[offset + 1];
      if ([0xc0, 0xc1, 0xc2, 0xc3, 0xc5, 0xc6, 0xc7, 0xc9, 0xca, 0xcb, 0xcd, 0xce, 0xcf].includes(marker)) {
        return { format: 'jpeg', height: buffer.readUInt16BE(offset + 5), width: buffer.readUInt16BE(offset + 7) };
      }
      if (offset + 4 > buffer.length) break;
      const length = buffer.readUInt16BE(offset + 2);
      if (length < 2) break;
      offset += 2 + length;
    }
    return { format: 'jpeg', width: null, height: null };
  }
  throw new Error('Downloaded body is not a recognized PNG, JPG, GIF, or WebP image');
}

const args = parseArgs(process.argv.slice(2));
if (args.help) {
  console.log('Usage: node verify-media.mjs --url https://... [--expected-content-type image/webp]');
  process.exit(0);
}
if (!args.url) throw new Error('--url is required');
const url = new URL(args.url);
if (url.protocol !== 'https:') throw new Error('Only HTTPS media URLs are accepted');

const response = await fetch(url, { redirect: 'follow', credentials: 'omit' });
if (!response.ok) throw new Error(`Anonymous GET failed: HTTP ${response.status}`);
const contentType = (response.headers.get('content-type') || '').split(';')[0].trim().toLowerCase();
if (!contentType.startsWith('image/')) throw new Error(`Unexpected Content-Type: ${contentType || '(missing)'}`);
if (args.expectedContentType && contentType !== args.expectedContentType) {
  throw new Error(`Expected ${args.expectedContentType}, received ${contentType}`);
}
const body = Buffer.from(await response.arrayBuffer());
const image = parseImage(body);
const result = {
  status: 'verified',
  anonymousHttpsGet: true,
  finalUrl: response.url,
  httpStatus: response.status,
  contentType,
  contentLength: body.length,
  cacheControl: response.headers.get('cache-control'),
  etagPresent: Boolean(response.headers.get('etag')),
  image,
};
console.log(JSON.stringify(result, null, 2));
