import { isIP } from 'node:net';

function ipv4Bytes(host) {
  if (isIP(host) !== 4) return null;
  const octets = host.split('.').map(Number);
  return octets.length === 4 && octets.every((value) => Number.isInteger(value) && value >= 0 && value <= 255) ? octets : null;
}

function ipv6Bytes(host) {
  if (isIP(host) !== 6) return null;
  const doubleColon = host.indexOf('::');
  if (doubleColon !== -1 && host.indexOf('::', doubleColon + 1) !== -1) return null;
  const expandPart = (part) => part ? part.split(':') : [];
  const left = expandPart(doubleColon === -1 ? host : host.slice(0, doubleColon));
  const right = expandPart(doubleColon === -1 ? '' : host.slice(doubleColon + 2));
  const convertEmbeddedIpv4 = (parts) => {
    if (!parts.length || !parts.at(-1).includes('.')) return parts;
    const bytes = ipv4Bytes(parts.at(-1));
    if (!bytes) return null;
    return [...parts.slice(0, -1), ((bytes[0] << 8) | bytes[1]).toString(16), ((bytes[2] << 8) | bytes[3]).toString(16)];
  };
  const leftParts = convertEmbeddedIpv4(left);
  const rightParts = convertEmbeddedIpv4(right);
  if (!leftParts || !rightParts) return null;
  const missing = 8 - leftParts.length - rightParts.length;
  if ((doubleColon === -1 && missing !== 0) || (doubleColon !== -1 && missing < 1)) return null;
  const words = [...leftParts, ...Array(Math.max(0, missing)).fill('0'), ...rightParts];
  if (words.length !== 8 || words.some((word) => !/^[0-9a-f]{1,4}$/i.test(word))) return null;
  return words.flatMap((word) => {
    const value = Number.parseInt(word, 16);
    return [value >> 8, value & 0xff];
  });
}

function isNonPublicIpv4(bytes) {
  const [a, b] = bytes;
  return a === 0
    || a === 10
    || a === 127
    || (a === 100 && b >= 64 && b <= 127)
    || (a === 169 && b === 254)
    || (a === 172 && b >= 16 && b <= 31)
    || (a === 192 && b === 0)
    || (a === 192 && b === 168)
    || (a === 198 && (b === 18 || b === 19))
    || a >= 224;
}

function isAllZero(bytes) {
  return bytes.every((byte) => byte === 0);
}

function isNonPublicIpv6(bytes) {
  if (isAllZero(bytes)) return true;
  if (bytes.slice(0, 15).every((byte) => byte === 0) && bytes[15] === 1) return true;
  if ((bytes[0] & 0xfe) === 0xfc) return true; // fc00::/7 unique local
  if (bytes[0] === 0xfe && (bytes[1] & 0xc0) === 0x80) return true; // fe80::/10 link local
  if (bytes[0] === 0xfe && (bytes[1] & 0xc0) === 0xc0) return true; // fec0::/10 deprecated site local
  if (bytes[0] === 0xff) return true; // multicast
  if (bytes[0] === 0x20 && bytes[1] === 0x01 && bytes[2] === 0x0d && bytes[3] === 0xb8) return true; // documentation

  const ipv4Mapped = bytes.slice(0, 10).every((byte) => byte === 0) && bytes[10] === 0xff && bytes[11] === 0xff;
  const ipv4Compatible = bytes.slice(0, 12).every((byte) => byte === 0);
  if (ipv4Mapped || ipv4Compatible) return isNonPublicIpv4(bytes.slice(12));
  return false;
}

export function isPrivateOrLocalHost(hostname) {
  const host = hostname.trim().toLowerCase().replace(/^\[|\]$/g, '').replace(/%25.*$/u, '');
  if (host === 'localhost' || host.endsWith('.localhost') || host.endsWith('.local')) return true;
  const version = isIP(host);
  if (version === 4) return isNonPublicIpv4(ipv4Bytes(host));
  if (version === 6) return isNonPublicIpv6(ipv6Bytes(host));
  return false;
}
