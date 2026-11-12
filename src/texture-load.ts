/** Network failures retry; queued loads have no arbitrary wall-clock expiry. */
interface TextureAsset { unload(): void }
interface TextureRegistry<A extends TextureAsset> {
  loadFromUrl(url: string, type: 'texture', callback: (error: unknown, asset?: A) => void): void;
  remove(asset: A): unknown;
}
interface LoadOptions { timeoutMs?: number; attempts?: number }

function loadOnce<A extends TextureAsset>(registry: TextureRegistry<A>, url: string,
                                         timeoutMs?: number): Promise<A> {
  return new Promise((resolve, reject) => {
    let expired = false;
    const timeout = timeoutMs === undefined ? undefined : setTimeout(() => {
      expired = true;
      reject(new Error('Texture decoding timed out.'));
    }, timeoutMs);
    registry.loadFromUrl(url, 'texture', (error, asset) => {
      clearTimeout(timeout);
      if (expired || error || !asset) {
        if (asset) {
          asset.unload();
          registry.remove(asset);
        }
        if (!expired) reject(new Error(String(error ?? 'Texture asset is missing')));
        return;
      }
      resolve(asset);
    });
  });
}

export async function loadTexture<A extends TextureAsset>(registry: TextureRegistry<A>, url: string,
                                                          options: LoadOptions={}): Promise<A> {
  const attempts = options.attempts ?? 3;
  if (attempts<1) throw new Error('Texture load requires at least one attempt');
  for (let attempt=0; ; attempt++) {
    try { return await loadOnce(registry,url,options.timeoutMs); }
    catch (error) {
      if (attempt+1>=attempts) throw error;
      await new Promise(resolve=>setTimeout(resolve,250*2**attempt));
    }
  }
}
