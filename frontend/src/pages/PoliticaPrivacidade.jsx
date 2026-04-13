import { Link } from 'react-router-dom'

export default function PoliticaPrivacidade() {
  return (
    <div className="min-h-screen bg-gray-50 py-12 px-4">
      <div className="max-w-3xl mx-auto bg-white rounded-xl shadow-sm p-8">
        <Link to="/login" className="text-indigo-600 hover:text-indigo-700 text-sm mb-6 inline-block">
          &larr; Voltar
        </Link>

        <h1 className="text-3xl font-bold text-gray-900 mb-2">Politica de Privacidade</h1>
        <p className="text-sm text-gray-500 mb-8">Ultima atualizacao: 12 de abril de 2026</p>

        <div className="prose prose-gray max-w-none space-y-6">
          <section>
            <h2 className="text-xl font-semibold text-gray-800 mb-3">1. Introducao</h2>
            <p className="text-gray-600 leading-relaxed">
              A Usina do Tempo ("nos", "nosso") respeita a privacidade dos usuarios e esta comprometida em proteger
              os dados pessoais coletados. Esta Politica de Privacidade descreve como coletamos, usamos, armazenamos
              e protegemos suas informacoes, em conformidade com a Lei Geral de Protecao de Dados (LGPD — Lei 13.709/2018).
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-gray-800 mb-3">2. Dados Coletados</h2>
            <p className="text-gray-600 leading-relaxed">Coletamos os seguintes dados:</p>
            <ul className="list-disc list-inside text-gray-600 space-y-1 mt-2">
              <li><strong>Dados de cadastro:</strong> nome, email, senha (criptografada), CPF/CNPJ, telefone</li>
              <li><strong>Dados de uso:</strong> acoes realizadas na plataforma, logs de acesso, metricas de uso</li>
              <li><strong>Dados de pagamento:</strong> processados pela Asaas (nao armazenamos dados de cartao)</li>
              <li><strong>Dados tecnicos:</strong> IP, user-agent, navegador</li>
              <li><strong>Conteudo gerado:</strong> textos, videos e midias criados pelo usuario na plataforma</li>
            </ul>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-gray-800 mb-3">3. Finalidade do Tratamento</h2>
            <p className="text-gray-600 leading-relaxed">Utilizamos seus dados para:</p>
            <ul className="list-disc list-inside text-gray-600 space-y-1 mt-2">
              <li>Fornecer e manter os servicos da Plataforma</li>
              <li>Processar pagamentos e gerenciar assinaturas</li>
              <li>Enviar comunicacoes sobre sua conta e servico</li>
              <li>Garantir a seguranca e prevenir fraudes</li>
              <li>Melhorar a experiencia do usuario e desenvolver novos recursos</li>
              <li>Cumprir obrigacoes legais e regulatorias</li>
            </ul>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-gray-800 mb-3">4. Base Legal (LGPD)</h2>
            <p className="text-gray-600 leading-relaxed">
              O tratamento dos dados pessoais e realizado com base nas seguintes hipoteses legais:
              execucao de contrato (Art. 7, V), consentimento (Art. 7, I), interesse legitimo (Art. 7, IX)
              e cumprimento de obrigacao legal (Art. 7, II).
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-gray-800 mb-3">5. Compartilhamento de Dados</h2>
            <p className="text-gray-600 leading-relaxed">
              Compartilhamos dados apenas com prestadores de servico essenciais para o funcionamento
              da Plataforma: Asaas (pagamentos), Supabase (banco de dados), Render (hospedagem),
              Google (YouTube API), Meta (Instagram API), Resend (email transacional).
              Nao vendemos dados pessoais a terceiros.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-gray-800 mb-3">6. Seguranca</h2>
            <p className="text-gray-600 leading-relaxed">
              Implementamos medidas de seguranca incluindo: criptografia em transito (HTTPS/TLS),
              criptografia de credenciais sensiveis em repouso (Fernet/AES), autenticacao JWT,
              controle de acesso por roles, isolamento de dados por workspace (RLS),
              protecao contra brute-force, rate limiting e auditoria de acessos.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-gray-800 mb-3">7. Seus Direitos (LGPD Art. 18)</h2>
            <p className="text-gray-600 leading-relaxed">Voce tem direito a:</p>
            <ul className="list-disc list-inside text-gray-600 space-y-1 mt-2">
              <li><strong>Acesso:</strong> solicitar copia de todos os seus dados</li>
              <li><strong>Correcao:</strong> atualizar dados incorretos ou incompletos</li>
              <li><strong>Exclusao:</strong> solicitar a eliminacao dos seus dados pessoais</li>
              <li><strong>Portabilidade:</strong> receber seus dados em formato estruturado (JSON)</li>
              <li><strong>Revogacao:</strong> retirar o consentimento a qualquer momento</li>
            </ul>
            <p className="text-gray-600 leading-relaxed mt-2">
              Para exercer seus direitos, acesse Configuracoes &gt; Privacidade na Plataforma ou envie email para{' '}
              <a href="mailto:privacidade@usinadotempo.com.br" className="text-indigo-600 hover:text-indigo-700">
                privacidade@usinadotempo.com.br
              </a>.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-gray-800 mb-3">8. Retencao de Dados</h2>
            <p className="text-gray-600 leading-relaxed">
              Mantemos seus dados enquanto sua conta estiver ativa. Logs de execucao sao retidos por 90 dias.
              Logs de auditoria sao retidos por 365 dias. Apos solicitar a exclusao, os dados serao anonimizados
              em ate 30 dias.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-gray-800 mb-3">9. Cookies</h2>
            <p className="text-gray-600 leading-relaxed">
              A Plataforma utiliza armazenamento local (localStorage) para manter sua sessao ativa.
              Nao utilizamos cookies de rastreamento ou analytics de terceiros.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-gray-800 mb-3">10. Contato do Encarregado (DPO)</h2>
            <p className="text-gray-600 leading-relaxed">
              Para questoes relacionadas a privacidade e protecao de dados, entre em contato:{' '}
              <a href="mailto:privacidade@usinadotempo.com.br" className="text-indigo-600 hover:text-indigo-700">
                privacidade@usinadotempo.com.br
              </a>
            </p>
          </section>
        </div>
      </div>
    </div>
  )
}
