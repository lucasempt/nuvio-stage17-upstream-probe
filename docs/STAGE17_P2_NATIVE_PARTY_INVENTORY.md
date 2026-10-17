# Stage17 P2 — Inventário do Watch Party nativo (somente upstream público)

> Escopo: `NuvioMedia/NuvioMobile` no commit `229c083cf3db7bab6fda284484f87439eb4e0eb0`.
> **Não contém código privado do Nuvio Together.** Não é um patch de remoção.
>
> Evidência: [GitHub Actions run #39048101577](https://github.com/lucasempt/nuvio-stage17-upstream-probe/actions/runs/39048101577) — `SUCCESS`, `STAGE17_P2_SOURCE_AUDIT=PASS`.

## Totais confirmados no log

| Medida | Quantidade |
| --- | ---: |
| Arquivos rastreados inspecionados (.kt/.xml etc.) | 1.401 |
| Arquivos com pelo menos uma correspondência de Party no scanner | 44 |
| Arquivos nativos em `features/party/` (inclui testes) | 14 |
| Arquivos de referências externas ao diretório nativo | 30 |
| Artefatos de build enviados | 0 |

**Limite importante:** correspondência do scanner não significa que o arquivo inteiro deva ser excluído. A busca inclui correspondências textuais genéricas (como `party`) e pode produzir falsos positivos ou não encontrar todos os vínculos dinâmicos.

## Núcleo Party nativo (14 arquivos, sendo 12 de implementação e 2 testes)

Implementação em `composeApp/src/commonMain/kotlin/com/nuvio/app/features/party/`:
`PartyApi.kt`, `PartyChannel.kt`, `PartyClock.kt`, `PartyCode.kt`,
`PartyDetails.kt`, `PartyModels.kt`, `PartyPanel.kt`,
`PartyRepository.kt`, `PartyScreen.kt`, `PartySourceMatch.kt`,
`PartySync.kt`, `PartyUi.kt`.

Testes em `composeApp/src/commonTest/kotlin/com/nuvio/app/features/party/`:
`PartyStreamTest.kt` e `PartySyncTest.kt`.

## Áreas externas com acoplamento real (auditoria de código e logs)

1. **Navegação e entrada**: `AppNavigationSupport.kt`, `MainAppContent.kt`, `SettingsDestinations.kt`, `navigation/Routes.kt`, `core/deeplink/AppUrlBridge.kt`, `androidApp/src/main/AndroidManifest.xml`. Cuidado para preservar esquemas e links não relacionados ao Party.
2. **Configurações e shell**: `AppShellComponents.kt`, `features/settings/SettingsScreen.kt`, `features/settings/SettingsRootPage.kt`.
3. **Seleção de fonte / player**: `StreamDestination.kt`, `PlayerDestination.kt`, `features/player/PlayerScreen.kt`, `PlayerScreenArgs.kt`, `PlayerScreenRuntimeParty.kt`, `PlayerScreenRuntimeState.kt`, `PlayerScreenRuntimeEffects.kt`, `PlayerScreenRuntimeGestureActions.kt`, `PlayerScreenRuntimePlaybackActions.kt`, `PlayerScreenRuntimeUi.kt`, `PlayerControlActions.kt`, `PlayerControls.kt`. As referências a sincronização, seek, taxa de reprodução, fonte compartilhada e controles precisam ser desacopladas cuidadosamente.
4. **Servidor / dados**: `core/network/ServerConfiguration.kt`, `core/network/ServerDiscovery.kt`, `androidMain/.../ServerConfigurationStorage.android.kt`, `iosMain/.../ServerConfigurationStorage.ios.kt`.
5. **Recursos e testes**: `composeResources/values/strings_party.xml` e `commonTest/.../core/deeplink/AppUrlBridgeTest.kt`; verificar referências a todas as strings e comportamentos de links antes de remover.

Outras correspondências genéricas a classificar manualmente: `features/p2p/P2pStreamingEngine.android.kt`, `features/p2p/P2pStreamingEngine.ios.kt`, `store.json`. **Não excluir automaticamente** esses arquivos; certas ocorrências podem ser texto não funcional.

## Sequência segura do patch, após esta auditoria

- **A. Preparação**: manter o commit de upstream fixo e criar patch apenas para uma cópia isolada do código público. Fazer inventário de símbolos e garantir que nenhum arquivo privado seja usado.
- **B. Interfaces / navegação**: remover rotas `PartyRoute`, links externos exclusivos do Watch Party, ações de configurações e controles que apontam ao Party original, mantendo funcionalidades não relacionadas.
- **C. Player e fontes (mais sensível)**: desacoplar `PartyRepository` e `PlayerScreenRuntimeParty`; revisar estados de controle, gestos, seek, taxa, efeitos, painel e destaque/compartilhamento de fonte. **Não remover reprodução normal nem fluxos de seleção de fonte.**
- **D. Backend / modelos / recursos**: remover, quando não houver consumidores, o núcleo do Party, testes exclusivos, `strings_party.xml` e capacidades `watchParty` que sejam estritamente nativas; preservar autenticação, Supabase e P2P não relacionados.
- **E. Gates obrigatórios**: busca por símbolos legados remanescentes, testes de links/configurações/player, `:androidApp:assembleFullDebug` sem erro, nenhum APK público distribuído.
- **F. Integração posterior**: incluir recursos de Together **somente** no ambiente privado, com testes independentes de integração. Este repositório público **não** é lugar para armazenar patches, chaves, identidade, protocolos ou artefatos privados.

## Proteções de escopo

- **Nenhuma alteração no upstream oficial**; sempre checkout temporário fixado por SHA.
- **Nenhuma alteração no repositório privado nesta etapa**.
- **Nenhuma mudança de orçamento, cobrança ou configurações de conta**.
- **Nenhum APK bruto publicado ou apresentado como Nuvio Together**.
- Este inventário é um checkpoint de auditoria, **não comprovação de remoção concluída**.
